package com.avatar.app.data.local.entity

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey
import java.math.BigDecimal
import java.time.Instant

enum class SaleStatus {
    DRAFT,
    PENDING,
    SENDING,
    SYNCED,
    REJECTED
}

@Entity(tableName = "pending_sales")
data class PendingSaleEntity(
    @PrimaryKey
    val clientUuid: String, // Idempotency-Key
    val customerId: Long,
    val customerName: String,
    val totalAmount: BigDecimal,
    val status: SaleStatus,
    val createdByUserEmail: String = "", // Güvenlik: Satışı oluşturan kullanıcının kimliği (kullanıcı karışıklığını önler)
    val serverSaleCode: String? = null,
    val serverSaleId: Long? = null,
    val errorCode: String? = null,
    val errorMessage: String? = null,
    val attemptCount: Int = 0,
    val createdAt: Instant = Instant.now(),
    val syncedAt: Instant? = null
)

@Entity(
    tableName = "pending_sale_lines",
    foreignKeys = [
        ForeignKey(
            entity = PendingSaleEntity::class,
            parentColumns = ["clientUuid"],
            childColumns = ["saleClientUuid"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index(value = ["saleClientUuid"])]
)
data class PendingSaleLineEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val saleClientUuid: String,
    val lotId: Long,
    val lotCode: String,
    val productName: String,
    val quantity: BigDecimal,
    val unitCode: String,
    val unitPrice: BigDecimal,
    val lineTotal: BigDecimal,
    val stockMovementId: Long? = null // sunucudan dönen stok hareketi kimliği (PDF şartı)
)

@Entity(tableName = "sync_state")
data class SyncStateEntity(
    @PrimaryKey
    val id: String = "GLOBAL_SYNC",
    val lastServerTime: String?,
    val lastSyncInstant: Instant = Instant.now()
)
