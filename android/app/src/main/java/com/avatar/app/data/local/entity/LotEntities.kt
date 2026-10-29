package com.avatar.app.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import java.math.BigDecimal

@Entity(tableName = "sellable_lots")
data class SellableLotEntity(
    @PrimaryKey
    val id: Long,
    val lotCode: String,
    val productId: Long,
    val productCode: String,
    val productName: String,
    val onHandQuantity: BigDecimal,
    val unitCode: String,
    val expiryDate: String?,
    val locationCode: String?,
    val salePrice: BigDecimal
)

@Entity(tableName = "blocked_lots")
data class BlockedLotEntity(
    @PrimaryKey
    val id: Long,
    val lotCode: String,
    val reasonCode: String?,
    val reasonText: String?,
    val blockedAt: String?
)
