package com.avatar.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.avatar.app.data.local.entity.CustomerEntity
import com.avatar.app.data.local.entity.SellableLotEntity
import com.avatar.app.data.repository.CreateSaleItem
import com.avatar.app.domain.validator.SaleValidator
import kotlinx.coroutines.launch
import java.math.BigDecimal
import java.math.RoundingMode

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NewSaleScreen(
    customers: List<CustomerEntity>,
    sellableLots: List<SellableLotEntity>,
    onCompleteSale: suspend (Long, String, List<CreateSaleItem>) -> Result<String>,
    onSaleCompleted: () -> Unit
) {
    val scope = rememberCoroutineScope()
    var selectedCustomer by remember { mutableStateOf<CustomerEntity?>(customers.firstOrNull()) }
    var customerDropdownExpanded by remember { mutableStateOf(false) }

    var selectedLot by remember { mutableStateOf<SellableLotEntity?>(sellableLots.firstOrNull()) }
    var lotDropdownExpanded by remember { mutableStateOf(false) }

    var quantityInput by remember { mutableStateOf("10") }
    var lineItems by remember { mutableStateOf(listOf<CreateSaleItem>()) }
    var isSubmitting by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var successDialogCode by remember { mutableStateOf<String?>(null) }

    // Otomatik satır toplamı ve genel toplam (BigDecimal)
    val grandTotal = remember(lineItems) {
        lineItems.fold(BigDecimal.ZERO) { acc, item ->
            acc + (item.quantity * item.unitPrice).setScale(2, RoundingMode.HALF_UP)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(16.dp)
    ) {
        Text(
            text = "Yeni Satış Oluştur",
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onBackground
        )

        errorMessage?.let { err ->
            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 8.dp)
            ) {
                Text(
                    text = err,
                    color = MaterialTheme.colorScheme.onErrorContainer,
                    modifier = Modifier.padding(10.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        // 1. Müşteri Seçimi
        ExposedDropdownMenuBox(
            expanded = customerDropdownExpanded,
            onExpandedChange = { customerDropdownExpanded = !customerDropdownExpanded }
        ) {
            OutlinedTextField(
                value = selectedCustomer?.let { "${it.name} (${it.code})" } ?: "Müşteri Seçin",
                onValueChange = {},
                readOnly = true,
                label = { Text("Market / Müşteri") },
                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = customerDropdownExpanded) },
                modifier = Modifier
                    .fillMaxWidth()
                    .menuAnchor(MenuAnchorType.PrimaryNotEditable)
            )
            ExposedDropdownMenu(
                expanded = customerDropdownExpanded,
                onDismissRequest = { customerDropdownExpanded = false }
            ) {
                customers.forEach { customer ->
                    DropdownMenuItem(
                        text = { Text("${customer.name} (${customer.code})") },
                        onClick = {
                            selectedCustomer = customer
                            customerDropdownExpanded = false
                        }
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // 2. Kalem Ekleme Bölümü
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(14.dp)) {
                Text(
                    text = "Ürün / Lot Ekle",
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 15.sp
                )

                Spacer(modifier = Modifier.height(8.dp))

                ExposedDropdownMenuBox(
                    expanded = lotDropdownExpanded,
                    onExpandedChange = { lotDropdownExpanded = !lotDropdownExpanded }
                ) {
                    OutlinedTextField(
                        value = selectedLot?.let { "${it.productName} | Lot: ${it.lotCode} (Stok: ${it.onHandQuantity.stripTrailingZeros().toPlainString()} ${it.unitCode})" } ?: "Lot Seçin",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Satılabilir Lot") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = lotDropdownExpanded) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .menuAnchor(MenuAnchorType.PrimaryNotEditable)
                    )
                    ExposedDropdownMenu(
                        expanded = lotDropdownExpanded,
                        onDismissRequest = { lotDropdownExpanded = false }
                    ) {
                        sellableLots.forEach { lot ->
                            DropdownMenuItem(
                                text = {
                                    Column {
                                        Text("${lot.productName} — Lot: ${lot.lotCode}", fontWeight = FontWeight.Medium)
                                        Text("Stok: ${lot.onHandQuantity.stripTrailingZeros().toPlainString()} ${lot.unitCode} | Fiyat: € ${lot.salePrice.toPlainString()}", fontSize = 12.sp, color = Color.Gray)
                                    }
                                },
                                onClick = {
                                    selectedLot = lot
                                    lotDropdownExpanded = false
                                }
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = quantityInput,
                        onValueChange = { quantityInput = it; errorMessage = null },
                        label = { Text("Miktar (${selectedLot?.unitCode ?: "Birim"})") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        singleLine = true,
                        modifier = Modifier.weight(1f)
                    )

                    OutlinedTextField(
                        value = "€ ${selectedLot?.salePrice?.toPlainString() ?: "0.00"}",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Sabit Fiyat") },
                        singleLine = true,
                        modifier = Modifier.weight(1f)
                    )
                }

                Spacer(modifier = Modifier.height(10.dp))

                Button(
                    onClick = {
                        val lot = selectedLot ?: return@Button
                        val qty = try { BigDecimal(quantityInput) } catch (_: Exception) { null }
                        if (qty == null || qty <= BigDecimal.ZERO) {
                            errorMessage = "Geçerli bir pozitif miktar girin."
                            return@Button
                        }
                        if (qty > lot.onHandQuantity) {
                            errorMessage = "Girilen miktar mevcut stoktan (${lot.onHandQuantity}) fazla olamaz."
                            return@Button
                        }

                        val existing = lineItems.find { it.lotId == lot.id }
                        if (existing != null) {
                            val newQty = existing.quantity + qty
                            if (newQty > lot.onHandQuantity) {
                                errorMessage = "Toplam satır miktarı mevcut stoktan fazla olamaz."
                                return@Button
                            }
                            lineItems = lineItems.map {
                                if (it.lotId == lot.id) it.copy(quantity = newQty) else it
                            }
                        } else {
                            lineItems = lineItems + CreateSaleItem(
                                lotId = lot.id,
                                lotCode = lot.lotCode,
                                productName = lot.productName,
                                quantity = qty,
                                unitCode = lot.unitCode,
                                unitPrice = lot.salePrice
                            )
                        }
                    },
                    modifier = Modifier.align(Alignment.End)
                ) {
                    Text("Kalem Ekle")
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        // 3. Eklenen Kalemler Listesi
        Text("Satış Kalemleri (${lineItems.size})", fontWeight = FontWeight.SemiBold)

        LazyColumn(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            items(lineItems) { item ->
                Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(10.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(item.productName, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                            Text("Lot: ${item.lotCode} | Miktar: ${item.quantity.stripTrailingZeros().toPlainString()} ${item.unitCode} × €${item.unitPrice.toPlainString()}", fontSize = 12.sp)
                        }
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                "€ ${(item.quantity * item.unitPrice).setScale(2, RoundingMode.HALF_UP).toPlainString()}",
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.padding(end = 8.dp)
                            )
                            IconButton(onClick = { lineItems = lineItems.filter { it.lotId != item.lotId } }) {
                                Text("✕", color = Color.Red, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }
        }

        Divider(modifier = Modifier.padding(vertical = 8.dp))

        // 4. Alt Toplam ve Tamamla Butonu
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text("Genel Toplam:", fontSize = 13.sp, color = Color.Gray)
                Text(
                    "€ ${grandTotal.toPlainString()}",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
            }

            Button(
                onClick = {
                    val cust = selectedCustomer ?: return@Button
                    scope.launch {
                        isSubmitting = true
                        errorMessage = null
                        val result = onCompleteSale(cust.id, cust.name, lineItems)
                        isSubmitting = false
                        if (result.isSuccess) {
                            successDialogCode = result.getOrNull()
                        } else {
                            errorMessage = result.exceptionOrNull()?.message ?: "Satış oluşturulamadı."
                        }
                    }
                },
                enabled = !isSubmitting && lineItems.isNotEmpty() && selectedCustomer != null,
                modifier = Modifier.height(48.dp)
            ) {
                if (isSubmitting) {
                    CircularProgressIndicator(modifier = Modifier.size(20.dp), color = Color.White)
                } else {
                    Text("Satışı Tamamla")
                }
            }
        }

        successDialogCode?.let { saleUuid ->
            AlertDialog(
                onDismissRequest = {
                    successDialogCode = null
                    onSaleCompleted()
                },
                title = { Text("Satış Başarıyla Kaydedildi") },
                text = {
                    Text("İşlem UUID: $saleUuid\n\nSatış yerel SQLite veritabanına işlendi. Çevrimiçiyse sunucuya aktarıldı, çevrimdışıysa bağlantı geldiğinde tek seferlik güvenli olarak gönderilecek.")
                },
                confirmButton = {
                    Button(onClick = {
                        successDialogCode = null
                        onSaleCompleted()
                    }) {
                        Text("Tamam")
                    }
                }
            )
        }
    }
}
