package com.avatar.app.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import com.avatar.app.data.local.converter.Converters
import com.avatar.app.data.local.dao.CustomerDao
import com.avatar.app.data.local.dao.LotDao
import com.avatar.app.data.local.dao.ProductDao
import com.avatar.app.data.local.dao.SaleDao
import com.avatar.app.data.local.dao.SyncStateDao
import com.avatar.app.data.local.entity.BlockedLotEntity
import com.avatar.app.data.local.entity.CustomerEntity
import com.avatar.app.data.local.entity.PendingSaleEntity
import com.avatar.app.data.local.entity.PendingSaleLineEntity
import com.avatar.app.data.local.entity.ProductEntity
import com.avatar.app.data.local.entity.SellableLotEntity
import com.avatar.app.data.local.entity.SyncStateEntity

@Database(
    entities = [
        ProductEntity::class,
        CustomerEntity::class,
        SellableLotEntity::class,
        BlockedLotEntity::class,
        PendingSaleEntity::class,
        PendingSaleLineEntity::class,
        SyncStateEntity::class
    ],
    version = 1,
    exportSchema = true
)
@TypeConverters(Converters::class)
abstract class AppDatabase : RoomDatabase() {
    abstract fun productDao(): ProductDao
    abstract fun customerDao(): CustomerDao
    abstract fun lotDao(): LotDao
    abstract fun saleDao(): SaleDao
    abstract fun syncStateDao(): SyncStateDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getDatabase(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "avatar_local.db"
                ).fallbackToDestructiveMigration()
                    .build()
                INSTANCE = instance
                instance
            }
        }

        fun createInMemoryDatabase(context: Context): AppDatabase {
            return Room.inMemoryDatabaseBuilder(
                context.applicationContext,
                AppDatabase::class.java
            ).build()
        }
    }
}
