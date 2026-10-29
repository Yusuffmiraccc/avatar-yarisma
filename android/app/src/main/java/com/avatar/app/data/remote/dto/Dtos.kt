package com.avatar.app.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class LoginRequest(
    val email: String,
    val password: String
)

@Serializable
data class RefreshRequest(
    @SerialName("refresh_token")
    val refreshToken: String
)

@Serializable
data class UserDto(
    val id: Long,
    val email: String,
    @SerialName("display_name")
    val displayName: String,
    val roles: List<String>,
    val permissions: List<String> = emptyList()
)

@Serializable
data class TokenResponse(
    @SerialName("access_token")
    val accessToken: String,
    @SerialName("refresh_token")
    val refreshToken: String,
    @SerialName("token_type")
    val tokenType: String = "bearer",
    @SerialName("expires_in")
    val expiresIn: Long,
    val user: UserDto
)

@Serializable
data class ProductSyncDto(
    val id: Long,
    val code: String,
    val name: String,
    @SerialName("product_type")
    val productType: String,
    @SerialName("base_unit_code")
    val baseUnitCode: String
)

@Serializable
data class CustomerSyncDto(
    val id: Long,
    val code: String,
    val name: String,
    @SerialName("customer_type")
    val customerType: String = "MARKET",
    val phone: String? = null,
    val email: String? = null
)

@Serializable
data class SellableLotSyncDto(
    val id: Long,
    @SerialName("lot_code")
    val lotCode: String,
    @SerialName("product_id")
    val productId: Long,
    @SerialName("product_code")
    val productCode: String? = null,
    @SerialName("product_name")
    val productName: String? = null,
    @SerialName("on_hand_quantity")
    val onHandQuantity: String,
    @SerialName("unit_code")
    val unitCode: String,
    @SerialName("expiry_date")
    val expiryDate: String? = null,
    @SerialName("location_code")
    val locationCode: String? = null,
    @SerialName("sale_price")
    val salePrice: String? = "0"
)

@Serializable
data class BlockedLotSyncDto(
    val id: Long,
    @SerialName("lot_code")
    val lotCode: String,
    @SerialName("reason_code")
    val reasonCode: String? = null,
    @SerialName("reason_text")
    val reasonText: String? = null,
    @SerialName("blocked_at")
    val blockedAt: String? = null
)

@Serializable
data class CatalogSyncResponse(
    @SerialName("server_time")
    val serverTime: String,
    val products: List<ProductSyncDto> = emptyList(),
    val customers: List<CustomerSyncDto> = emptyList(),
    @SerialName("sellable_lots")
    val sellableLots: List<SellableLotSyncDto> = emptyList(),
    @SerialName("blocked_lots")
    val blockedLots: List<BlockedLotSyncDto> = emptyList(),
    @SerialName("blocked_lot_ids")
    val blockedLotIds: List<Long> = emptyList()
)

@Serializable
data class SaleLineRequest(
    @SerialName("lot_id")
    val lotId: Long,
    val quantity: String
)

@Serializable
data class SaleCreateRequest(
    @SerialName("customer_id")
    val customerId: Long,
    @SerialName("sold_at")
    val soldAt: String,
    val lines: List<SaleLineRequest>
)

@Serializable
data class SaleLineResponse(
    val id: Long,
    @SerialName("lot_id")
    val lotId: Long,
    @SerialName("lot_code")
    val lotCode: String,
    val quantity: String,
    @SerialName("unit_price")
    val unitPrice: String,
    @SerialName("line_total")
    val lineTotal: String,
    @SerialName("stock_movement_id")
    val stockMovementId: Long? = null
)

@Serializable
data class SaleResponse(
    val id: Long,
    @SerialName("sale_code")
    val saleCode: String,
    @SerialName("customer_id")
    val customerId: Long,
    @SerialName("total_amount")
    val totalAmount: String,
    val lines: List<SaleLineResponse>
)

@Serializable
data class ErrorDetail(
    val code: String,
    val message: String,
    val details: Map<String, String>? = null
)

@Serializable
data class ErrorEnvelope(
    val error: ErrorDetail,
    @SerialName("request_id")
    val requestId: String? = null
)
