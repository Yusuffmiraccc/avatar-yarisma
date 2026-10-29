package com.avatar.app.data.sync

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.avatar.app.AvatarApp

class SalesUploadWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result {
        val app = applicationContext as? AvatarApp ?: return Result.failure()
        return try {
            val uploadResult = app.salesRepository.uploadAllPendingSales()
            // Satış sonrası stok tazeliği için katalog senkronunu tetikle
            app.catalogRepository.syncCatalog()
            if (uploadResult.isSuccess) {
                Result.success()
            } else {
                if (runAttemptCount < 5) Result.retry() else Result.failure()
            }
        } catch (e: Exception) {
            if (runAttemptCount < 5) Result.retry() else Result.failure()
        }
    }
}

class CatalogSyncWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result {
        val app = applicationContext as? AvatarApp ?: return Result.failure()
        return try {
            val syncResult = app.catalogRepository.syncCatalog()
            if (syncResult.isSuccess) Result.success() else Result.retry()
        } catch (e: Exception) {
            Result.retry()
        }
    }
}
