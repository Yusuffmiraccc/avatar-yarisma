package com.avatar.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.avatar.app.ui.screens.CatalogScreen
import com.avatar.app.ui.screens.HomeScreen
import com.avatar.app.ui.screens.LoginScreen
import com.avatar.app.ui.screens.NewSaleScreen
import com.avatar.app.ui.screens.SalesHistoryScreen
import com.avatar.app.ui.screens.SettingsScreen
import com.avatar.app.ui.theme.AvatarAppTheme
import kotlinx.coroutines.launch

sealed class Screen(val route: String, val title: String) {
    object Login : Screen("login", "Giriş")
    object Home : Screen("home", "Ana Sayfa")
    object Catalog : Screen("catalog", "Stok / Katalog")
    object NewSale : Screen("new_sale", "Yeni Satış")
    object History : Screen("history", "Geçmiş")
    object Settings : Screen("settings", "Ayarlar")
}

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val app = application as AvatarApp
        val authRepo = app.authRepository
        val catalogRepo = app.catalogRepository
        val salesRepo = app.salesRepository

        setContent {
            AvatarAppTheme {
                var isLoggedIn by remember { mutableStateOf(authRepo.isLoggedIn()) }
                val navController = rememberNavController()
                val scope = rememberCoroutineScope()

                val syncState by produceState(initialValue = null as com.avatar.app.data.local.entity.SyncStateEntity?) {
                    value = catalogRepo.getSyncState()
                }
                val sellableLots by catalogRepo.sellableLots.collectAsState(initial = emptyList())
                val blockedLots by catalogRepo.blockedLots.collectAsState(initial = emptyList())
                val products by catalogRepo.products.collectAsState(initial = emptyList())
                val customers by catalogRepo.customers.collectAsState(initial = emptyList())
                val allSales by salesRepo.allSales.collectAsState(initial = emptyList())

                if (!isLoggedIn) {
                    LoginScreen(
                        onLoginSuccess = {
                            isLoggedIn = true
                            scope.launch { catalogRepo.syncCatalog() }
                        },
                        onLoginClick = { email, password ->
                            authRepo.login(email, password).map { }
                        }
                    )
                } else {
                    val navBackStackEntry by navController.currentBackStackEntryAsState()
                    val currentRoute = navBackStackEntry?.destination?.route

                    Scaffold(
                        bottomBar = {
                            NavigationBar {
                                NavigationBarItem(
                                    selected = currentRoute == Screen.Home.route,
                                    onClick = { navController.navigate(Screen.Home.route) },
                                    label = { Text("Ana Sayfa") },
                                    icon = { Text("🏠") }
                                )
                                NavigationBarItem(
                                    selected = currentRoute == Screen.Catalog.route,
                                    onClick = { navController.navigate(Screen.Catalog.route) },
                                    label = { Text("Katalog") },
                                    icon = { Text("📦") }
                                )
                                NavigationBarItem(
                                    selected = currentRoute == Screen.NewSale.route,
                                    onClick = { navController.navigate(Screen.NewSale.route) },
                                    label = { Text("Satış") },
                                    icon = { Text("🛒") }
                                )
                                NavigationBarItem(
                                    selected = currentRoute == Screen.History.route,
                                    onClick = { navController.navigate(Screen.History.route) },
                                    label = { Text("Geçmiş") },
                                    icon = { Text("📋") }
                                )
                                NavigationBarItem(
                                    selected = currentRoute == Screen.Settings.route,
                                    onClick = { navController.navigate(Screen.Settings.route) },
                                    label = { Text("Ayarlar") },
                                    icon = { Text("⚙️") }
                                )
                            }
                        }
                    ) { innerPadding ->
                        NavHost(
                            navController = navController,
                            startDestination = Screen.Home.route,
                            modifier = Modifier.padding(innerPadding)
                        ) {
                            composable(Screen.Home.route) {
                                HomeScreen(
                                    syncState = syncState,
                                    sellableLots = sellableLots,
                                    blockedLots = blockedLots,
                                    allSales = allSales,
                                    onSyncClick = { catalogRepo.syncCatalog() },
                                    onNavigateToNewSale = { navController.navigate(Screen.NewSale.route) },
                                    onNavigateToCatalog = { navController.navigate(Screen.Catalog.route) },
                                    onNavigateToHistory = { navController.navigate(Screen.History.route) }
                                )
                            }
                            composable(Screen.Catalog.route) {
                                CatalogScreen(
                                    sellableLots = sellableLots,
                                    blockedLots = blockedLots
                                )
                            }
                            composable(Screen.NewSale.route) {
                                NewSaleScreen(
                                    customers = customers,
                                    sellableLots = sellableLots,
                                    onCompleteSale = { custId, custName, items ->
                                        salesRepo.createSale(custId, custName, items)
                                    },
                                    onSaleCompleted = {
                                        navController.navigate(Screen.History.route)
                                    }
                                )
                            }
                            composable(Screen.History.route) {
                                SalesHistoryScreen(
                                    sales = allSales,
                                    onRetrySale = { uuid -> salesRepo.uploadSingleSale(uuid) },
                                    onDeleteSale = { uuid -> salesRepo.deleteSale(uuid) }
                                )
                            }
                            composable(Screen.Settings.route) {
                                SettingsScreen(
                                    userEmail = authRepo.tokenManager.userEmail,
                                    userDisplayName = authRepo.tokenManager.userDisplayName,
                                    pendingSalesCount = allSales.count { it.sale.status == com.avatar.app.data.local.entity.SaleStatus.PENDING },
                                    onLogoutClick = {
                                        authRepo.logout()
                                        isLoggedIn = false
                                    }
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
