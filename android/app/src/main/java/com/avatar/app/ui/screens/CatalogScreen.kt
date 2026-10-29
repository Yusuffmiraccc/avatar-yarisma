package com.avatar.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.avatar.app.data.local.entity.BlockedLotEntity
import com.avatar.app.data.local.entity.SellableLotEntity

@Composable
fun CatalogScreen(
    sellableLots: List<SellableLotEntity>,
    blockedLots: List<BlockedLotEntity>
) {
    var selectedTab by remember { mutableStateOf(0) }
    var searchQuery by remember { mutableStateOf("") }

    val filteredSellable = remember(sellableLots, searchQuery) {
        if (searchQuery.isBlank()) sellableLots
        else sellableLots.filter {
            it.productName.contains(searchQuery, ignoreCase = true) ||
            it.lotCode.contains(searchQuery, ignoreCase = true)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        TabRow(selectedTabIndex = selectedTab) {
            Tab(
                selected = selectedTab == 0,
                onClick = { selectedTab = 0 },
                text = { Text("Satılabilir (${sellableLots.size})") }
            )
            Tab(
                selected = selectedTab == 1,
                onClick = { selectedTab = 1 },
                text = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("Bloke Lotlar")
                        if (blockedLots.isNotEmpty()) {
                            Badge(
                                containerColor = MaterialTheme.colorScheme.error,
                                modifier = Modifier.padding(start = 4.dp)
                            ) {
                                Text("${blockedLots.size}")
                            }
                        }
                    }
                }
            )
        }

        if (selectedTab == 0) {
            OutlinedTextField(
                value = searchQuery,
                onValueChange = { searchQuery = it },
                placeholder = { Text("Ürün adı veya lot kodu ara...") },
                singleLine = true,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp)
            )

            if (filteredSellable.isEmpty()) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Text("Stokta satılabilir ürün bulunamadı.", color = Color.Gray)
                }
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(filteredSellable, key = { it.id }) { lot ->
                        Card(modifier = Modifier.fillMaxWidth()) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.Top
                                ) {
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(
                                            text = lot.productName,
                                            fontWeight = FontWeight.Bold,
                                            fontSize = 16.sp
                                        )
                                        Text(
                                            text = "Lot: ${lot.lotCode}",
                                            fontSize = 13.sp,
                                            color = MaterialTheme.colorScheme.primary,
                                            fontWeight = FontWeight.Medium
                                        )
                                    }
                                    Column(horizontalAlignment = Alignment.End) {
                                        Text(
                                            text = "€ ${lot.salePrice.toPlainString()}",
                                            fontWeight = FontWeight.Bold,
                                            fontSize = 16.sp,
                                            color = MaterialTheme.colorScheme.primary
                                        )
                                        Text(
                                            text = "Sabit Liste Fiyatı",
                                            fontSize = 10.sp,
                                            color = Color.Gray
                                        )
                                    }
                                }

                                Spacer(modifier = Modifier.height(8.dp))

                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Text(
                                        text = "Mevcut Stok: ${lot.onHandQuantity.stripTrailingZeros().toPlainString()} ${lot.unitCode}",
                                        fontSize = 13.sp,
                                        fontWeight = FontWeight.SemiBold,
                                        color = if (lot.onHandQuantity.toDouble() > 0) Color(0xFF15803D) else Color.Red
                                    )
                                    lot.expiryDate?.let {
                                        Text(
                                            text = "SKT: $it",
                                            fontSize = 12.sp,
                                            color = Color.DarkGray
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        } else {
            // Bloke Lotlar Tabı
            if (blockedLots.isEmpty()) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Text("Sistemde aktif bloke edilmiş veya geri çağrılmış lot bulunmuyor.", color = Color.Gray)
                }
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    items(blockedLots, key = { it.id }) { blocked ->
                        Card(
                            colors = CardDefaults.cardColors(containerColor = Color(0xFFFEF2F2)),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text(
                                        text = blocked.lotCode,
                                        fontSize = 18.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = Color(0xFF991B1B)
                                    )
                                    Badge(containerColor = Color(0xFFDC2626)) {
                                        Text("GERİ ÇAĞRILDI / BLOKE", color = Color.White, fontWeight = FontWeight.Bold)
                                    }
                                }

                                Spacer(modifier = Modifier.height(8.dp))

                                Text(
                                    text = "Neden: ${blocked.reasonText ?: blocked.reasonCode ?: "Belirtilmedi"}",
                                    fontSize = 13.sp,
                                    color = Color(0xFF7F1D1D)
                                )
                                Text(
                                    text = "Uygulama Kuralı: Bu lot satışta seçilemez. Çevrimdışı eski önbellekle gönderilmeye çalışılsa dahi sunucu (409 LOT_BLOCKED) reddeder.",
                                    fontSize = 11.sp,
                                    color = Color.DarkGray,
                                    modifier = Modifier.padding(top = 4.dp)
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
