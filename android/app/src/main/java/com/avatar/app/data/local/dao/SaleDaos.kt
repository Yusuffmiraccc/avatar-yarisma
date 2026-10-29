package com.avatar.app.data.local.dao

import androidx.room.Dao
import androidx.room.Embedded
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Relation
import androidx.room.Transaction
import androidx.room.Update
import com.avatar.app.data.local.entity.PendingSaleEntity
import com.avatar.app.data.local.entity.PendingSaleLineEntity
import com.avatar.app.data.local.entity.SaleStatus
import com.avatar.app.data.local.entity.SyncStateEntity
import kotlinx.coroutines.flow.Flow
import java.time.Instant

data class SaleWithLines(
    @Embedded val sale: PendingSaleEntity,
    @Relation(
        parentColumn = "clientUuid",
        entityColumn = "saleClientUuid"
    )
    val lines: List<PendingSaleLineEntity>
)

@Dao
interface SaleDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertSale(sale: PendingSaleEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertSaleLines(lines: List<PendingSaleLineEntity>)

    @Transaction
    suspend fun insertSaleWithLines(sale: PendingSaleEntity, lines: List<PendingSaleLineEntity>) {
        insertSale(sale)
        insertSaleLines(lines)
    }

    @Transaction
    @Query("SELECT * FROM pending_sales ORDER BY createdAt DESC")
    fun getAllSalesWithLines(): Flow<List<SaleWithLines>>

    @Transaction
    @Query("SELECT * FROM pending_sales WHERE status = :status ORDER BY createdAt ASC")
    suspend fun getSalesByStatus(status: SaleStatus): List<SaleWithLines>

    @Transaction
    @Query("SELECT * FROM pending_sales WHERE clientUuid = :clientUuid LIMIT 1")
    suspend fun getSaleWithLines(clientUuid: String): SaleWithLines?

    @Query("UPDATE pending_sales SET status = :status, attemptCount = attemptCount + 1 WHERE clientUuid = :clientUuid")
    suspend fun updateSaleStatus(clientUuid: String, status: SaleStatus)

    @Transaction
    suspend fun markSaleSynced(
        clientUuid: String,
        serverSaleCode: String,
        serverSaleId: Long,
        syncedLines: List<Pair<Long, Long>> // lotId -> stockMovementId
    ) {
        updateSaleSuccess(clientUuid, serverSaleCode, serverSaleId, Instant.now())
        for ((lotId, stockMovementId) in syncedLines) {
            updateLineStockMovement(clientUuid, lotId, stockMovementId)
        }
    }

    @Query("UPDATE pending_sales SET status = 'SYNCED', serverSaleCode = :code, serverSaleId = :saleId, syncedAt = :syncedAt WHERE clientUuid = :clientUuid")
    suspend fun updateSaleSuccess(clientUuid: String, code: String, saleId: Long, syncedAt: Instant)

    @Query("UPDATE pending_sale_lines SET stockMovementId = :stockMovementId WHERE saleClientUuid = :clientUuid AND lotId = :lotId")
    suspend fun updateLineStockMovement(clientUuid: String, lotId: Long, stockMovementId: Long)

    @Query("UPDATE pending_sales SET status = 'REJECTED', errorCode = :code, errorMessage = :message WHERE clientUuid = :clientUuid")
    suspend fun markSaleRejected(clientUuid: String, code: String, message: String)

    @Query("DELETE FROM pending_sales WHERE clientUuid = :clientUuid")
    suspend fun deleteSale(clientUuid: String)
}

@Dao
interface SyncStateDao {
    @Query("SELECT * FROM sync_state WHERE id = 'GLOBAL_SYNC' LIMIT 1")
    suspend fun getSyncState(): SyncStateEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun setSyncState(state: SyncStateEntity)
}
