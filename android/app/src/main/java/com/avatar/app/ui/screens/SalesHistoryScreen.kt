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
import com.avatar.app.data.local.dao.SaleWithLines
import com.avatar.app.data.local.entity.SaleStatus
import kotlinx.coroutines.launch

@Composable
fun SalesHistoryScreen(
    sales: List<SaleWithLines>,
    onRetrySale: suspend (String) -> Unit,
    onDeleteSale: suspend (String) -> Unit
) {
    val scope = rememberCoroutineScope()
    var selectedFilter by remember { mutableStateOf<SaleStatus?>(null) }

    val filteredSales = remember(sales, selectedFilter) {
        if (selectedFilter == null) sales
        else sales.filter { it.sale.status == selectedFilter }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(16.dp)
    ) {
        Text(
            text = "Satış Geçmişi & Senkron Kuyruğu",
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onBackground
        )

        Spacer(modifier = Modifier.height(12.dp))

        // Filtre Çipleri
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            FilterChip(
                selected = selectedFilter == null,
                onClick = { selectedFilter = null },
                label = { Text("Tümü (${sales.size})") }
            )
            FilterChip(
                selected = selectedFilter == SaleStatus.PENDING,
                onClick = { selectedFilter = SaleStatus.PENDING },
                label = { Text("Bekleyen (${sales.count { it.sale.status == SaleStatus.PENDING || it.sale.status == SaleStatus.SENDING }})") }
            )
            FilterChip(
                selected = selectedFilter == SaleStatus.SYNCED,
                onClick = { selectedFilter = SaleStatus.SYNCED },
                label = { Text("Kayıtlı (${sales.count { it.sale.status == SaleStatus.SYNCED }})") }
            )
            FilterChip(
                selected = selectedFilter == SaleStatus.REJECTED,
                onClick = { selectedFilter = SaleStatus.REJECTED },
                label = { Text("Reddedilen (${sales.count { it.sale.status == SaleStatus.REJECTED }})") }
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        if (filteredSales.isEmpty()) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Text("Bu kategoride satış kaydı bulunmuyor.", color = Color.Gray)
            }
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                items(filteredSales, key = { it.sale.clientUuid }) { item ->
                    val sale = item.sale
                    val lines = item.lines

                    val statusColor = when (sale.status) {
                        SaleStatus.SYNCED -> Color(0xFF15803D)
                        SaleStatus.PENDING, SaleStatus.SENDING -> Color(0xFFD97706)
                        SaleStatus.REJECTED -> Color(0xFFDC2626)
                        SaleStatus.DRAFT -> Color.Gray
                    }

                    val statusText = when (sale.status) {
                        SaleStatus.SYNCED -> "KAYDEDİLDİ"
                        SaleStatus.PENDING -> "KUYRUKTA BEKLİYOR"
                        SaleStatus.SENDING -> "GÖNDERİLİYOR"
                        SaleStatus.REJECTED -> "REDDEDİLDİ"
                        SaleStatus.DRAFT -> "TASLAK"
                    }

                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = if (sale.status == SaleStatus.REJECTED) Color(0xFFFEF2F2) else MaterialTheme.colorScheme.surface
                        )
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = sale.customerName,
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 16.sp
                                )
                                Badge(containerColor = statusColor) {
                                    Text(statusText, color = Color.White, fontWeight = FontWeight.Bold)
                                }
                            }

                            Spacer(modifier = Modifier.height(4.dp))

                            Text(
                                text = "Idempotency-Key (UUID): ${sale.clientUuid}",
                                fontSize = 11.sp,
                                color = Color.Gray
                            )

                            sale.serverSaleCode?.let { code ->
                                Text(
                                    text = "Sunucu Satış Kodu: $code (ID: ${sale.serverSaleId})",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = MaterialTheme.colorScheme.primary
                                )
                            }

                            Spacer(modifier = Modifier.height(8.dp))

                            // Satır Kalemleri ve Stok Hareketi Bilgisi (PDF Zorunlu Gereksinimi)
                            Text("Satır Detayları:", fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = Color.DarkGray)
                            lines.forEach { line ->
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(vertical = 2.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Column {
                                        Text("${line.productName} (Lot: ${line.lotCode})", fontSize = 13.sp)
                                        Text(
                                            "${line.quantity.stripTrailingZeros().toPlainString()} ${line.unitCode} × €${line.unitPrice.toPlainString()}" +
                                                    (line.stockMovementId?.let { " | Stok Hareketi #$it" } ?: ""),
                                            fontSize = 11.sp,
                                            color = Color.Gray
                                        )
                                    }
                                    Text("€ ${line.lineTotal.toPlainString()}", fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                                }
                            }

                            Divider(modifier = Modifier.padding(vertical = 6.dp))

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text("Toplam Tutar:", fontWeight = FontWeight.Bold)
                                Text("€ ${sale.totalAmount.toPlainString()}", fontWeight = FontWeight.Bold, fontSize = 16.sp, color = MaterialTheme.colorScheme.primary)
                            }

                            // Reddedilen Satış Yönetimi
                            if (sale.status == SaleStatus.REJECTED) {
                                Spacer(modifier = Modifier.height(8.dp))
                                Text(
                                    text = "Reddetme Sebebi: [${sale.errorCode}] ${sale.errorMessage}",
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFFB91C1C)
                                )

                                Spacer(modifier = Modifier.height(8.dp))

                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.End,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    OutlinedButton(
                                        onClick = { scope.launch { onDeleteSale(sale.clientUuid) } },
                                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.Red),
                                        contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp)
                                    ) {
                                        Text("Kuyruktan Sil", fontSize = 12.sp)
                                    }

                                    Spacer(modifier = Modifier.width(8.dp))

                                    Button(
                                        onClick = { scope.launch { onRetrySale(sale.clientUuid) } },
                                        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp)
                                    ) {
                                        Text("Tekrar Gönder", fontSize = 12.sp)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
