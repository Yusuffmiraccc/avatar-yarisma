package com.avatar.app.data.repository

import android.content.Context
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import com.avatar.app.data.local.AppDatabase
import com.avatar.app.data.local.dao.SaleWithLines
import com.avatar.app.data.local.entity.PendingSaleEntity
import com.avatar.app.data.local.entity.PendingSaleLineEntity
import com.avatar.app.data.local.entity.SaleStatus
import com.avatar.app.data.remote.api.ApiClient
import com.avatar.app.data.remote.dto.ErrorEnvelope
import com.avatar.app.data.remote.dto.SaleCreateRequest
import com.avatar.app.data.remote.dto.SaleLineRequest
import com.avatar.app.data.sync.SalesUploadWorker
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import java.math.BigDecimal
import java.math.RoundingMode
import java.time.Instant
import java.util.UUID
import java.util.concurrent.TimeUnit

data class CreateSaleItem(
    val lotId: Long,
    val lotCode: String,
    val productName: String,
    val quantity: BigDecimal,
    val unitCode: String,
    val unitPrice: BigDecimal
)

class SalesRepository(
    private val context: Context,
    private val db: AppDatabase,
    private val apiClient: ApiClient
) {
    private val jsonParser = Json { ignoreUnknownKeys = true }

    val allSales: Flow<List<SaleWithLines>> = db.saleDao().getAllSalesWithLines()

    suspend fun getSale(clientUuid: String): SaleWithLines? = db.saleDao().getSaleWithLines(clientUuid)

    suspend fun deleteSale(clientUuid: String) {
        db.saleDao().deleteSale(clientUuid)
    }

    suspend fun createSale(
        customerId: Long,
        customerName: String,
        items: List<CreateSaleItem>
    ): Result<String> = withContext(Dispatchers.IO) {
        if (items.isEmpty()) {
            return@withContext Result.failure(IllegalArgumentException("Satış için en az bir kalem eklenmelidir."))
        }

        // 1. Bloke lot kontrolü (Anında doğrulama)
        for (item in items) {
            if (db.lotDao().isLotBlocked(item.lotId, item.lotCode)) {
                return@withContext Result.failure(IllegalStateException("Lot ${item.lotCode} bloke edilmiştir/geri çağrılmıştır; satılamaz!"))
            }
        }

        // 2. Miktar ve eldeki stok kontrolü
        for (item in items) {
            if (item.quantity <= BigDecimal.ZERO) {
                return@withContext Result.failure(IllegalArgumentException("Miktar 0'dan büyük olmalıdır."))
            }
            val lot = db.lotDao().getSellableLotById(item.lotId)
            if (lot == null || item.quantity > lot.onHandQuantity) {
                return@withContext Result.failure(IllegalStateException("${item.productName} (${item.lotCode}) için yetersiz stok! Mevcut: ${lot?.onHandQuantity ?: 0}"))
            }
        }

        // 3. Kalıcı client_uuid (Idempotency-Key) üretimi
        val clientUuid = UUID.randomUUID().toString()
        val now = Instant.now()

        // 4. Parasal hesaplamalar: BigDecimal, ROUND_HALF_UP, asla Double değil
        var totalAmount = BigDecimal.ZERO
        val lineEntities = items.map { item ->
            val lineTotal = (item.quantity * item.unitPrice).setScale(2, RoundingMode.HALF_UP)
            totalAmount += lineTotal
            PendingSaleLineEntity(
                saleClientUuid = clientUuid,
                lotId = item.lotId,
                lotCode = item.lotCode,
                productName = item.productName,
                quantity = item.quantity.setScale(3, RoundingMode.HALF_UP),
                unitCode = item.unitCode,
                unitPrice = item.unitPrice.setScale(2, RoundingMode.HALF_UP),
                lineTotal = lineTotal
            )
        }

        val currentUserEmail = apiClient.tokenManager.userEmail ?: ""
        val saleEntity = PendingSaleEntity(
            clientUuid = clientUuid,
            customerId = customerId,
            customerName = customerName,
            totalAmount = totalAmount.setScale(2, RoundingMode.HALF_UP),
            status = SaleStatus.PENDING,
            createdByUserEmail = currentUserEmail,
            createdAt = now
        )

        // 5. Tek Room transaction'ında kaydet ve yerel stoktan iyimser düşüm uygula
        db.saleDao().insertSaleWithLines(saleEntity, lineEntities)
        for (item in items) {
            db.lotDao().optimisticDeductStock(item.lotId, item.quantity)
        }

        // 6. Arka plan WorkManager görevini planla
        enqueueUploadWork()

        // 7. Çevrimiçiyse hemen yüklemeyi dene
        try {
            uploadSingleSale(clientUuid)
        } catch (_: Exception) {
            // Çevrimdışıysa veya anlık hata verdiyse kuyrukta kalır
        }

        Result.success(clientUuid)
    }

    suspend fun uploadSingleSale(clientUuid: String): Result<Unit> = withContext(Dispatchers.IO) {
        val saleWithLines = db.saleDao().getSaleWithLines(clientUuid)
            ?: return@withContext Result.failure(Exception("Satış bulunamadı: $clientUuid"))

        if (saleWithLines.sale.status == SaleStatus.SYNCED) {
            return@withContext Result.success(Unit)
        }

        // Güvenlik denetimi: Aktif oturum bu satışı oluşturan kullanıcıya mı ait?
        val currentEmail = apiClient.tokenManager.userEmail
        if (saleWithLines.sale.createdByUserEmail.isNotBlank() &&
            currentEmail != null &&
            !saleWithLines.sale.createdByUserEmail.equals(currentEmail, ignoreCase = true)
        ) {
            // Başka bir kullanıcının bekleyen satışı bu oturumda gönderilemez!
            val mismatchError = "Satış '${saleWithLines.sale.createdByUserEmail}' tarafından oluşturuldu. " +
                "Mevcut oturum ($currentEmail) bu satışı gönderemez. Lütfen asıl kullanıcı ile giriş yapın."
            db.saleDao().updateSaleStatus(clientUuid, SaleStatus.PENDING)
            return@withContext Result.failure(SecurityException(mismatchError))
        }

        // Kimlik denetimi: Oturum kapalıysa satış PENDING olarak güvende kalır
        if (!apiClient.tokenManager.isLoggedIn()) {
            db.saleDao().updateSaleStatus(clientUuid, SaleStatus.PENDING)
            return@withContext Result.failure(IllegalStateException("Oturum süresi dolmuş veya kapalı. Lütfen giriş yapın."))
        }

        db.saleDao().updateSaleStatus(clientUuid, SaleStatus.SENDING)

        val request = SaleCreateRequest(
            customerId = saleWithLines.sale.customerId,
            soldAt = saleWithLines.sale.createdAt.toString(),
            lines = saleWithLines.lines.map {
                SaleLineRequest(
                    lotId = it.lotId,
                    quantity = it.quantity.toPlainString()
                )
            }
        )

        try {
            val response = apiClient.saleApi.createSale(
                idempotencyKey = clientUuid,
                request = request
            )

            if (response.isSuccessful && response.body() != null) {
                val body = response.body()!!
                val syncedLines = body.lines.mapNotNull { line ->
                    line.stockMovementId?.let { smId -> Pair(line.lotId, smId) }
                }
                db.saleDao().markSaleSynced(
                    clientUuid = clientUuid,
                    serverSaleCode = body.saleCode,
                    serverSaleId = body.id,
                    syncedLines = syncedLines
                )
                Result.success(Unit)
            } else {
                val code = response.code()
                val errorBody = response.errorBody()?.string()
                val errorEnvelope = try {
                    errorBody?.let { jsonParser.decodeFromString<ErrorEnvelope>(it) }
                } catch (_: Exception) {
                    null
                }

                val errCode = errorEnvelope?.error?.code ?: "HTTP_$code"
                val errMsg = errorEnvelope?.error?.message ?: response.message()

                when (code) {
                    401 -> {
                        // Token süresi dolmuş veya parola sunucuda değişmiş;
                        // Satış asla silinmez, kuyrukta güvenle saklanır, kullanıcı yeniden girişe yönlendirilir.
                        db.saleDao().updateSaleStatus(clientUuid, SaleStatus.PENDING)
                        apiClient.tokenManager.accessToken = null
                        Result.failure(Exception("Oturum süresi doldu veya parola değişti. Lütfen tekrar giriş yapın."))
                    }
                    409 -> {
                        // Kalıcı çakışma (LOT_BLOCKED, INSUFFICIENT_STOCK)
                        val userFriendlyMessage = when (errCode) {
                            "LOT_BLOCKED" -> "Bu lot geri çağrılmış/bloke edilmiştir; satışı sunucu tarafından reddedildi."
                            "INSUFFICIENT_STOCK" -> "Sunucuda yetersiz stok; başka kanaldan satılmış olabilir."
                            "IDEMPOTENCY_KEY_REUSED" -> "Bu işlem anahtarı daha önce farklı içerikle kullanılmış."
                            else -> errMsg
                        }
                        db.saleDao().markSaleRejected(clientUuid, errCode, userFriendlyMessage)
                        Result.failure(Exception(userFriendlyMessage))
                    }
                    400, 403, 404 -> {
                        // Kalıcı doğrulama hatası
                        db.saleDao().markSaleRejected(clientUuid, errCode, errMsg)
                        Result.failure(Exception(errMsg))
                    }
                    else -> {
                        // Geçici hata (5xx, 429 vb.); PENDING durumuna dön
                        db.saleDao().updateSaleStatus(clientUuid, SaleStatus.PENDING)
                        Result.failure(Exception("Geçici sunucu hatası: $code"))
                    }
                }
            }
        } catch (e: Exception) {
            db.saleDao().updateSaleStatus(clientUuid, SaleStatus.PENDING)
            Result.failure(e)
        }
    }

    suspend fun uploadAllPendingSales(): Result<Unit> = withContext(Dispatchers.IO) {
        val pending = db.saleDao().getSalesByStatus(SaleStatus.PENDING)
        var allOk = true
        for (sale in pending) {
            val res = uploadSingleSale(sale.sale.clientUuid)
            if (res.isFailure) {
                allOk = false
            }
        }
        if (allOk) Result.success(Unit) else Result.failure(Exception("Bazı satışlar yüklenemedi."))
    }

    fun enqueueUploadWork() {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val uploadRequest = OneTimeWorkRequestBuilder<SalesUploadWorker>()
            .setConstraints(constraints)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 15, TimeUnit.SECONDS)
            .build()

        WorkManager.getInstance(context).enqueueUniqueWork(
            "avatar_sales_upload",
            ExistingWorkPolicy.APPEND_OR_REPLACE,
            uploadRequest
        )
    }
}
