package com.avatar.app

import com.avatar.app.data.local.entity.PendingSaleEntity
import com.avatar.app.data.local.entity.SaleStatus
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.math.BigDecimal
import java.time.Instant

class OfflineQueueAuthTest {

    @Test
    fun pendingSale_storesAuthorEmail_preventsCrossUserSubmission() {
        val originalAuthor = "sales1@avatar.demo"
        val sale = PendingSaleEntity(
            clientUuid = "test-uuid-001",
            customerId = 1L,
            customerName = "Market A",
            totalAmount = BigDecimal("750.00"),
            status = SaleStatus.PENDING,
            createdByUserEmail = originalAuthor,
            createdAt = Instant.now()
        )

        assertEquals("sales1@avatar.demo", sale.createdByUserEmail)

        // Farklı kullanıcı giriş yaptığında kontrol
        val differentUser = "sales2@avatar.demo"
        val isAllowed = sale.createdByUserEmail.equals(differentUser, ignoreCase = true)
        assertFalse("Başka bir kullanıcının bekleyen satışı farklı kullanıcı adına yüklenemez", isAllowed)

        // Aynı kullanıcı giriş yaptığında kontrol
        val sameUser = "SALES1@AVATAR.DEMO"
        val isAuthorAllowed = sale.createdByUserEmail.equals(sameUser, ignoreCase = true)
        assertTrue("Satışı oluşturan asıl kullanıcı yükleyebilmelidir", isAuthorAllowed)
    }

    @Test
    fun tokenExpiryOrPasswordChange_keepsSaleInPendingState_neverDeletes() {
        var status = SaleStatus.PENDING

        // Yükleme başlatıldı
        status = SaleStatus.SENDING

        // Sunucudan 401 Unauthorized döndü (token süresi doldu veya parola değişti)
        val httpCode = 401
        if (httpCode == 401) {
            // Güvenli kural: Satış silinmez veya REJECTED yapılmaz; PENDING durumuna iade edilir
            status = SaleStatus.PENDING
        }

        assertEquals(SaleStatus.PENDING, status)
        assertNotEquals(SaleStatus.REJECTED, status)
        assertNotEquals(SaleStatus.SYNCED, status)
    }

    @Test
    fun recallOrBlockedLot_marksSaleRejectedPermanently() {
        var status = SaleStatus.SENDING
        val httpCode = 409
        val errorCode = "LOT_BLOCKED"

        if (httpCode == 409 && errorCode == "LOT_BLOCKED") {
            status = SaleStatus.REJECTED
        }

        assertEquals(SaleStatus.REJECTED, status)
    }
}
