package com.avatar.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.avatar.app.data.local.dao.SaleWithLines
import com.avatar.app.data.local.entity.BlockedLotEntity
import com.avatar.app.data.local.entity.SaleStatus
import com.avatar.app.data.local.entity.SellableLotEntity
import com.avatar.app.data.local.entity.SyncStateEntity
import kotlinx.coroutines.launch

@Composable
fun HomeScreen(
    syncState: SyncStateEntity?,
    sellableLots: List<SellableLotEntity>,
    blockedLots: List<BlockedLotEntity>,
    allSales: List<SaleWithLines>,
    onSyncClick: suspend () -> Result<Unit>,
    onNavigateToNewSale: () -> Unit,
    onNavigateToCatalog: () -> Unit,
    onNavigateToHistory: () -> Unit
) {
    val scope = rememberCoroutineScope()
    var isSyncing by remember { mutableStateOf(false) }
    var syncMessage by remember { mutableStateOf<String?>(null) }

    val pendingCount = allSales.count { it.sale.status == SaleStatus.PENDING || it.sale.status == SaleStatus.SENDING }
    val rejectedCount = allSales.count { it.sale.status == SaleStatus.REJECTED }
    val syncedCount = allSales.count { it.sale.status == SaleStatus.SYNCED }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(16.dp)
            .verticalScroll(rememberScrollState())
    ) {
        // Senkron Durum Şeridi (Bölüm 5.1 & 6.2 gereği)
        Card(
            colors = CardDefaults.cardColors(
                containerColor = if (syncState != null) Color(0xFFF0FDF4) else Color(0xFFFEF2F2)
            ),
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = if (syncState != null) "Bağlantı: Çevrimiçi" else "Bağlantı: Çevrimdışı (Yerel Önbellek)",
                        fontWeight = FontWeight.SemiBold,
                        color = if (syncState != null) Color(0xFF166534) else Color(0xFF991B1B)
                    )
                    Text(
                        text = "Son Senkron: ${syncState?.lastServerTime ?: "Henüz yapılmadı"}",
                        fontSize = 12.sp,
                        color = Color.Gray
                    )
                }

                Button(
                    onClick = {
                        scope.launch {
                            isSyncing = true
                            syncMessage = null
                            val res = onSyncClick()
                            isSyncing = false
                            syncMessage = if (res.isSuccess) "Senkron başarılı" else "Senkron hatası: ${res.exceptionOrNull()?.message}"
                        }
                    },
                    enabled = !isSyncing,
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                ) {
                    if (isSyncing) {
                        CircularProgressIndicator(modifier = Modifier.size(16.dp), color = Color.White)
                    } else {
                        Text("Senkronla", fontSize = 12.sp)
                    }
                }
            }
        }

        syncMessage?.let {
            Text(
                text = it,
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier.padding(top = 4.dp, bottom = 8.dp)
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "Operasyon Göstergeleri",
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onBackground
        )

        Spacer(modifier = Modifier.height(12.dp))

        // Özet Kartları
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Card(modifier = Modifier.weight(1f)) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text("Satılabilir Lot", fontSize = 12.sp, color = Color.Gray)
                    Text("${sellableLots.size}", fontSize = 24.sp, fontWeight = FontWeight.Bold)
                }
            }
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0xFFFEF2F2)),
                modifier = Modifier.weight(1f)
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text("Bloke Lotlar", fontSize = 12.sp, color = Color(0xFF991B1B))
                    Text(
                        "${blockedLots.size}",
                        fontSize = 24.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFFB91C1C)
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = if (pendingCount > 0) Color(0xFFFFFBEB) else Color(0xFFF8FAFC)
                ),
                modifier = Modifier.weight(1f)
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text("Kuyrukta Bekleyen", fontSize = 12.sp, color = Color(0xFFB45309))
                    Text(
                        "$pendingCount",
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (pendingCount > 0) Color(0xFFD97706) else Color.DarkGray
                    )
                }
            }
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = if (rejectedCount > 0) Color(0xFFFEF2F2) else Color(0xFFF8FAFC)
                ),
                modifier = Modifier.weight(1f)
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text("Reddedilen Satış", fontSize = 12.sp, color = Color(0xFF991B1B))
                    Text(
                        "$rejectedCount",
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (rejectedCount > 0) Color(0xFFDC2626) else Color.DarkGray
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        Text(
            text = "Hızlı İşlemler",
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onBackground
        )

        Spacer(modifier = Modifier.height(12.dp))

        Button(
            onClick = onNavigateToNewSale,
            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp)
        ) {
            Text("Yeni Satış Oluştur", fontSize = 16.sp)
        }

        Spacer(modifier = Modifier.height(8.dp))

        OutlinedButton(
            onClick = onNavigateToCatalog,
            modifier = Modifier
                .fillMaxWidth()
                .height(48.dp)
        ) {
            Text("Stok & Lot Kataloğu")
        }

        Spacer(modifier = Modifier.height(8.dp))

        OutlinedButton(
            onClick = onNavigateToHistory,
            modifier = Modifier
                .fillMaxWidth()
                .height(48.dp)
        ) {
            Text("Satış Geçmişi & Kuyruk ($syncedCount başarılı, $pendingCount bekleyen)")
        }
    }
}
