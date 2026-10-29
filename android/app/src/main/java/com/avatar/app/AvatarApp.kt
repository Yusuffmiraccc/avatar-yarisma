package com.avatar.app

import android.app.Application
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.avatar.app.data.local.AppDatabase
import com.avatar.app.data.remote.api.ApiClient
import com.avatar.app.data.repository.AuthRepository
import com.avatar.app.data.repository.CatalogRepository
import com.avatar.app.data.repository.SalesRepository
import com.avatar.app.data.sync.CatalogSyncWorker
import java.util.concurrent.TimeUnit

class AvatarApp : Application() {
    lateinit var database: AppDatabase
        private set

    lateinit var apiClient: ApiClient
        private set

    lateinit var authRepository: AuthRepository
        private set

    lateinit var catalogRepository: CatalogRepository
        private set

    lateinit var salesRepository: SalesRepository
        private set

    override fun onCreate() {
        super.onCreate()

        database = AppDatabase.getDatabase(this)
        apiClient = ApiClient(this)
        authRepository = AuthRepository(apiClient)
        catalogRepository = CatalogRepository(database, apiClient)
        salesRepository = SalesRepository(this, database, apiClient)

        setupPeriodicCatalogSync()
    }

    private fun setupPeriodicCatalogSync() {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val syncRequest = PeriodicWorkRequestBuilder<CatalogSyncWorker>(15, TimeUnit.MINUTES)
            .setConstraints(constraints)
            .build()

        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "avatar_periodic_catalog_sync",
            ExistingPeriodicWorkPolicy.KEEP,
            syncRequest
        )
    }
}
