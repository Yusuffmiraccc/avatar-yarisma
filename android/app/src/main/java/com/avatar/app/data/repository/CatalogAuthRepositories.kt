package com.avatar.app.data.repository

import com.avatar.app.data.local.AppDatabase
import com.avatar.app.data.local.entity.BlockedLotEntity
import com.avatar.app.data.local.entity.CustomerEntity
import com.avatar.app.data.local.entity.ProductEntity
import com.avatar.app.data.local.entity.SellableLotEntity
import com.avatar.app.data.local.entity.SyncStateEntity
import com.avatar.app.data.remote.api.ApiClient
import com.avatar.app.data.remote.dto.LoginRequest
import com.avatar.app.data.remote.dto.TokenResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import java.math.BigDecimal
import java.time.Instant

class AuthRepository(
    private val apiClient: ApiClient
) {
    val tokenManager = apiClient.tokenManager

    suspend fun login(email: String, password: String): Result<TokenResponse> = withContext(Dispatchers.IO) {
        try {
            val response = apiClient.authApi.login(LoginRequest(email.trim(), password))
            if (response.isSuccessful && response.body() != null) {
                val tokens = response.body()!!
                tokenManager.saveTokens(tokens)
                Result.success(tokens)
            } else {
                val errorMsg = when (response.code()) {
                    401 -> "E-posta veya parola hatalı."
                    429 -> "Çok fazla başarısız deneme. Lütfen bir süre bekleyin."
                    else -> "Giriş başarısız oldu (Hata: ${response.code()})"
                }
                Result.failure(Exception(errorMsg))
            }
        } catch (e: Exception) {
            Result.failure(Exception("Sunucuya bağlanılamadı: ${e.localizedMessage}"))
        }
    }

    fun logout() {
        // Çıkış bekleyen satışları SİLMEZ; yalnızca yerel oturum token'larını temizler (PDF Kuralı)
        tokenManager.clear()
    }

    fun isLoggedIn(): Boolean = tokenManager.isLoggedIn()
}

class CatalogRepository(
    private val db: AppDatabase,
    private val apiClient: ApiClient
) {
    val sellableLots: Flow<List<SellableLotEntity>> = db.lotDao().getAllSellableLots()
    val blockedLots: Flow<List<BlockedLotEntity>> = db.lotDao().getAllBlockedLots()
    val products: Flow<List<ProductEntity>> = db.productDao().getAllProducts()
    val customers: Flow<List<CustomerEntity>> = db.customerDao().getAllCustomers()

    fun searchSellableLots(query: String): Flow<List<SellableLotEntity>> =
        db.lotDao().searchSellableLots(query)

    fun searchCustomers(query: String): Flow<List<CustomerEntity>> =
        db.customerDao().searchCustomers(query)

    suspend fun getSyncState(): SyncStateEntity? = db.syncStateDao().getSyncState()

    suspend fun isLotBlocked(lotId: Long, lotCode: String): Boolean =
        db.lotDao().isLotBlocked(lotId, lotCode)

    suspend fun syncCatalog(): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val lastState = db.syncStateDao().getSyncState()
            val response = apiClient.catalogApi.getCatalog(updatedAfter = lastState?.lastServerTime)
            if (!response.isSuccessful || response.body() == null) {
                return@withContext Result.failure(Exception("Senkron başarısız: HTTP ${response.code()}"))
            }

            val body = response.body()!!

            // Tüm değişiklikler tek Room transaction'ında uygulanır (Bölüm 5 Kuralı)
            val productEntities = body.products.map {
                ProductEntity(it.id, it.code, it.name, it.productType, it.baseUnitCode)
            }
            val customerEntities = body.customers.map {
                CustomerEntity(it.id, it.code, it.name, it.customerType, it.phone, it.email)
            }
            val lotEntities = body.sellableLots.map {
                SellableLotEntity(
                    id = it.id,
                    lotCode = it.lotCode,
                    productId = it.productId,
                    productCode = it.productCode ?: "",
                    productName = it.productName ?: it.lotCode,
                    onHandQuantity = BigDecimal(it.onHandQuantity),
                    unitCode = it.unitCode,
                    expiryDate = it.expiryDate,
                    locationCode = it.locationCode,
                    salePrice = BigDecimal(it.salePrice ?: "0")
                )
            }
            val blockedEntities = body.blockedLots.map {
                BlockedLotEntity(
                    id = it.id,
                    lotCode = it.lotCode,
                    reasonCode = it.reasonCode,
                    reasonText = it.reasonText,
                    blockedAt = it.blockedAt
                )
            }.toMutableList()

            for (blockedId in body.blockedLotIds) {
                if (blockedEntities.none { it.id == blockedId }) {
                    blockedEntities.add(
                        BlockedLotEntity(
                            id = blockedId,
                            lotCode = "LOT-$blockedId",
                            reasonCode = "RECALL_BLOCKED",
                            reasonText = "Sunucu tarafından bloke edilmiştir.",
                            blockedAt = null
                        )
                    )
                }
            }

            // 1. Ürün ve müşteriler artımlı güncellenir
            db.productDao().upsertProducts(productEntities)
            db.customerDao().upsertCustomers(customerEntities)

            // 2. Satılabilir ve bloke lot tabloları TAM YENİLENİR
            db.lotDao().replaceSellableLots(lotEntities)
            db.lotDao().replaceBlockedLots(blockedEntities)

            // 3. Sunucu zamanı kaydedilir
            db.syncStateDao().setSyncState(
                SyncStateEntity(
                    id = "GLOBAL_SYNC",
                    lastServerTime = body.serverTime,
                    lastSyncInstant = Instant.now()
                )
            )

            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
