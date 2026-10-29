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
    onLogoutClick: () -> Unit
) {
    var showLogoutConfirm by remember { mutableStateOf(false) }

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
                Text("Varsayılan Adres: http://10.0.2.2:8000/api/v1/", fontSize = 13.sp)
                Text("Fiziksel Cihaz İçin: adb reverse tcp:8000 tcp:8000", fontSize = 12.sp, color = Color.Gray)
                Text("Güvenlik: Yalnızca debug modda loopback HTTP açıktır; prodüksiyonda cleartext kapalıdır.", fontSize = 11.sp, color = Color.DarkGray, modifier = Modifier.padding(top = 4.dp))
            }
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
