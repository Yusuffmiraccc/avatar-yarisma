package com.avatar.app.data.remote.api

import com.avatar.app.data.remote.dto.CatalogSyncResponse
import com.avatar.app.data.remote.dto.LoginRequest
import com.avatar.app.data.remote.dto.RefreshRequest
import com.avatar.app.data.remote.dto.SaleCreateRequest
import com.avatar.app.data.remote.dto.SaleResponse
import com.avatar.app.data.remote.dto.TokenResponse
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Query

interface AuthApi {
    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): Response<TokenResponse>

    @POST("auth/refresh")
    suspend fun refresh(@Body request: RefreshRequest): Response<TokenResponse>
}

interface CatalogApi {
    @GET("sync/catalog")
    suspend fun getCatalog(
        @Query("updated_after") updatedAfter: String? = null
    ): Response<CatalogSyncResponse>
}

interface SaleApi {
    @POST("sales")
    suspend fun createSale(
        @Header("Idempotency-Key") idempotencyKey: String,
        @Body request: SaleCreateRequest
    ): Response<SaleResponse>
}
