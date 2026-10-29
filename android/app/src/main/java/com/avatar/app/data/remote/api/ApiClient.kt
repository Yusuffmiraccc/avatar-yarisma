package com.avatar.app.data.remote.api

import android.content.Context
import com.avatar.app.data.remote.dto.RefreshRequest
import com.avatar.app.data.remote.dto.TokenResponse
import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import kotlinx.serialization.json.Json
import okhttp3.Authenticator
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import java.util.concurrent.TimeUnit

class TokenManager(context: Context) {
    private val prefs = context.getSharedPreferences("avatar_secure_auth", Context.MODE_PRIVATE)

    var accessToken: String?
        get() = prefs.getString("access_token", null)
        set(value) = prefs.edit().putString("access_token", value).apply()

    var refreshToken: String?
        get() = prefs.getString("refresh_token", null)
        set(value) = prefs.edit().putString("refresh_token", value).apply()

    var userDisplayName: String?
        get() = prefs.getString("user_name", null)
        set(value) = prefs.edit().putString("user_name", value).apply()

    var userEmail: String?
        get() = prefs.getString("user_email", null)
        set(value) = prefs.edit().putString("user_email", value).apply()

    fun saveTokens(tokens: TokenResponse) {
        prefs.edit()
            .putString("access_token", tokens.accessToken)
            .putString("refresh_token", tokens.refreshToken)
            .putString("user_name", tokens.user.displayName)
            .putString("user_email", tokens.user.email)
            .apply()
    }

    fun clear() {
        prefs.edit().clear().apply()
    }

    fun isLoggedIn(): Boolean = !accessToken.isNullOrBlank()
}

class ApiClient(
    private val context: Context,
    baseUrl: String = "http://10.0.2.2:8000/api/v1/"
) {
    val tokenManager = TokenManager(context)

    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        encodeDefaults = true
    }

    private val authInterceptor = Interceptor { chain ->
        val original = chain.request()
        val builder = original.newBuilder()
        tokenManager.accessToken?.let { token ->
            builder.header("Authorization", "Bearer $token")
        }
        builder.header("Accept", "application/json")
        chain.proceed(builder.build())
    }

    // Refresh serialization: single-flight lock prevents concurrent 401s from invalidating family
    private val tokenAuthenticator = object : Authenticator {
        private val refreshLock = Any()

        override fun authenticate(route: Route?, response: Response): Request? {
            val originalAccessToken = response.request.header("Authorization")?.removePrefix("Bearer ")

            synchronized(refreshLock) {
                // If token already refreshed by another concurrent call, replay immediately with new token
                val currentAccessToken = tokenManager.accessToken
                if (currentAccessToken != null && currentAccessToken != originalAccessToken) {
                    return response.request.newBuilder()
                        .header("Authorization", "Bearer $currentAccessToken")
                        .build()
                }

                val currentRefreshToken = tokenManager.refreshToken ?: return null

                // Perform synchronous refresh call
                try {
                    val refreshCall = rawAuthApi.refresh(RefreshRequest(currentRefreshToken))
                    val execute = refreshCall.execute()
                    if (execute.isSuccessful && execute.body() != null) {
                        val newTokens = execute.body()!!
                        tokenManager.saveTokens(newTokens)
                        return response.request.newBuilder()
                            .header("Authorization", "Bearer ${newTokens.accessToken}")
                            .build()
                    } else {
                        // Refresh failed or revoked; keep local sales queue, but require re-login
                        tokenManager.accessToken = null
                        return null
                    }
                } catch (e: Exception) {
                    return null // Network error; retry later
                }
            }
        }
    }

    private val rawClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    // Standalone retrofit for unauthenticated refresh calls
    private val rawAuthRetrofit = Retrofit.Builder()
        .baseUrl(baseUrl)
        .client(rawClient)
        .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
        .build()

    private interface RawAuthService {
        @retrofit2.http.POST("auth/refresh")
        fun refresh(@retrofit2.http.Body request: RefreshRequest): retrofit2.Call<TokenResponse>
    }

    private val rawAuthApi = rawAuthRetrofit.create(RawAuthService::class.java)

    private val logging = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BASIC
    }

    private val okHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .addInterceptor(authInterceptor)
        .addInterceptor(logging)
        .authenticator(tokenAuthenticator)
        .build()

    private val retrofit = Retrofit.Builder()
        .baseUrl(baseUrl)
        .client(okHttpClient)
        .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
        .build()

    val authApi: AuthApi = retrofit.create(AuthApi::class.java)
    val catalogApi: CatalogApi = retrofit.create(CatalogApi::class.java)
    val saleApi: SaleApi = retrofit.create(SaleApi::class.java)
}
