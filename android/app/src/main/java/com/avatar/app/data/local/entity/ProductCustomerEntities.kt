package com.avatar.app.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "products")
data class ProductEntity(
    @PrimaryKey
    val id: Long,
    val code: String,
    val name: String,
    val productType: String,
    val baseUnitCode: String
)

@Entity(tableName = "customers")
data class CustomerEntity(
    @PrimaryKey
    val id: Long,
    val code: String,
    val name: String,
    val customerType: String,
    val phone: String?,
    val email: String?
)
