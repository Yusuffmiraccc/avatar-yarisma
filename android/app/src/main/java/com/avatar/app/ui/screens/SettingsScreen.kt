package com.avatar.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun SettingsScreen(
    userEmail: String?,
    userDisplayName: String?,
    pendingSalesCount: Int,
    currentServerUrl: String = "http://10.0.2.2:8000/api/v1/",
    onServerUrlChange: ((String) -> Unit)? = null,
    onLogoutClick: () -> Unit
) {
    var showLogoutConfirm by remember { mutableStateOf(false) }
    var showServerDialog by remember { mutableStateOf(false) }
    var tempUrl by remember(currentServerUrl) { mutableStateOf(currentServerUrl) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(16.dp)
    ) {
        Text(
            text = "Uygulama Ayarları",
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onBackground
        )

        Spacer(modifier = Modifier.height(16.dp))

        // Kullanıcı Profili Kartı
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(14.dp)) {
                Text("Aktif Oturum", fontWeight = FontWeight.SemiBold, fontSize = 15.sp)
                Spacer(modifier = Modifier.height(6.dp))
                Text("Kullanıcı: ${userDisplayName ?: "Demo Satış"}", fontWeight = FontWeight.Medium)
                Text("E-posta: ${userEmail ?: "sales@avatar.demo"}", color = Color.Gray, fontSize = 13.sp)
                Text("Rol: SALES (Fiyat Düzenleme Yetkisi Yoktur)", color = MaterialTheme.colorScheme.primary, fontSize = 12.sp, modifier = Modifier.padding(top = 4.dp))
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Ağ ve Sunucu Bilgisi
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(14.dp)) {
                Text("Ağ Yapılandırması", fontWeight = FontWeight.SemiBold, fontSize = 15.sp)
                Spacer(modifier = Modifier.height(6.dp))
                Text("Aktif Sunucu Adresi: $currentServerUrl", fontSize = 13.sp, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Medium)
                Text("Gerçek telefonda yerel PC IP'si (ör: http://192.168.1.50:8000/api/v1/) kullanılmalıdır.", fontSize = 12.sp, color = Color.Gray, modifier = Modifier.padding(top = 2.dp))
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedButton(
                    onClick = { showServerDialog = true },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Sunucu Adresini Değiştir")
                }
            }
        }

        if (showServerDialog) {
            AlertDialog(
                onDismissRequest = { showServerDialog = false },
                title = { Text("Sunucu API Adresi") },
                text = {
                    Column {
                        Text(
                            "Backend sunucusunun IP veya alan adını girin (ör: http://192.168.1.50:8000/api/v1/):",
                            fontSize = 12.sp
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        OutlinedTextField(
                            value = tempUrl,
                            onValueChange = { tempUrl = it },
                            label = { Text("API Base URL") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            SuggestionChip(
                                onClick = { tempUrl = "http://10.0.2.2:8000/api/v1/" },
                                label = { Text("Emülatör") }
                            )
                            SuggestionChip(
                                onClick = { tempUrl = "http://localhost:8000/api/v1/" },
                                label = { Text("USB / Local") }
                            )
                        }
                    }
                },
                confirmButton = {
                    Button(onClick = {
                        onServerUrlChange?.invoke(tempUrl)
                        showServerDialog = false
                    }) {
                        Text("Kaydet")
                    }
                },
                dismissButton = {
                    OutlinedButton(onClick = { showServerDialog = false }) {
                        Text("İptal")
                    }
                }
            )
        }

        Spacer(modifier = Modifier.height(24.dp))

        // Çıkış Butonu
        Button(
            onClick = { showLogoutConfirm = true },
            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error),
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Oturumu Kapat")
        }

        if (showLogoutConfirm) {
            AlertDialog(
                onDismissRequest = { showLogoutConfirm = false },
                title = { Text("Oturum Kapatılsın mı?") },
                text = {
                    Text(
                        if (pendingSalesCount > 0)
                            "Kuyrukta $pendingSalesCount adet henüz gönderilmemiş satış bulunmaktadır. Oturumu kapatsanız dahi bekleyen satışlar Room veritabanında silinmeden korunur ve tekrar giriş yapıldığında aktarılacaktır."
                        else
                            "Oturumunuz kapatılacaktır. Devam etmek istiyor musunuz?"
                    )
                },
                confirmButton = {
                    Button(
                        onClick = {
                            showLogoutConfirm = false
                            onLogoutClick()
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                    ) {
                        Text("Çıkış Yap")
                    }
                },
                dismissButton = {
                    OutlinedButton(onClick = { showLogoutConfirm = false }) {
                        Text("İptal")
                    }
                }
            )
        }
    }
}
