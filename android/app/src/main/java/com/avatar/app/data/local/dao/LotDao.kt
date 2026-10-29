package com.avatar.app.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Transaction
import com.avatar.app.data.local.entity.BlockedLotEntity
import com.avatar.app.data.local.entity.SellableLotEntity
import kotlinx.coroutines.flow.Flow
import java.math.BigDecimal

@Dao
interface LotDao {
    @Query("SELECT * FROM sellable_lots WHERE onHandQuantity > 0 ORDER BY productName ASC, lotCode ASC")
    fun getAllSellableLots(): Flow<List<SellableLotEntity>>

    @Query("SELECT * FROM sellable_lots WHERE (productName LIKE '%' || :query || '%' OR lotCode LIKE '%' || :query || '%') AND onHandQuantity > 0 ORDER BY productName ASC")
    fun searchSellableLots(query: String): Flow<List<SellableLotEntity>>

    @Query("SELECT * FROM sellable_lots WHERE id = :id LIMIT 1")
    suspend fun getSellableLotById(id: Long): SellableLotEntity?

    @Query("DELETE FROM sellable_lots")
    suspend fun clearSellableLots()

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertSellableLots(lots: List<SellableLotEntity>)

    @Transaction
    suspend fun replaceSellableLots(lots: List<SellableLotEntity>) {
        clearSellableLots()
        insertSellableLots(lots)
    }

    @Query("SELECT * FROM blocked_lots ORDER BY lotCode ASC")
    fun getAllBlockedLots(): Flow<List<BlockedLotEntity>>

    @Query("SELECT EXISTS(SELECT 1 FROM blocked_lots WHERE id = :lotId OR lotCode = :lotCode)")
    suspend fun isLotBlocked(lotId: Long, lotCode: String): Boolean

    @Query("DELETE FROM blocked_lots")
    suspend fun clearBlockedLots()

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertBlockedLots(lots: List<BlockedLotEntity>)

    @Transaction
    suspend fun replaceBlockedLots(lots: List<BlockedLotEntity>) {
        clearBlockedLots()
        insertBlockedLots(lots)
    }

    @Query("UPDATE sellable_lots SET onHandQuantity = onHandQuantity - :deduction WHERE id = :lotId AND onHandQuantity >= :deduction")
    suspend fun optimisticDeductStock(lotId: Long, deduction: BigDecimal): Int
}
