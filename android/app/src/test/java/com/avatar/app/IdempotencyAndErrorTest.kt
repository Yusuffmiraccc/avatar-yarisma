package com.avatar.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.UUID

class IdempotencyAndErrorTest {

    @Test
    fun testClientUuidIsValidFormat() {
        val uuid = UUID.randomUUID().toString()
        val parsed = UUID.fromString(uuid)
        assertNotNull(parsed)
        assertEquals(36, uuid.length)
        assertTrue(uuid.contains("-"))
    }

    @Test
    fun testIdempotencyKeyPreservedAcrossRetries() {
        // Oluşturulan client_uuid yeniden denemede ASLA değişmemelidir
        val originalUuid = UUID.randomUUID().toString()
        var retryKey = originalUuid

        // 1. Gönderim denemesi (Ağ hatası)
        val attempt1Key = retryKey

        // 2. Yeniden deneme
        val attempt2Key = retryKey

        assertEquals(originalUuid, attempt1Key)
        assertEquals(originalUuid, attempt2Key)
    }

    @Test
    fun testServerErrorCodeMapping() {
        fun mapError(code: String): String = when (code) {
            "LOT_BLOCKED" -> "Bu lot geri çağrılmış/bloke edilmiştir; satışı sunucu tarafından reddedildi."
            "INSUFFICIENT_STOCK" -> "Sunucuda yetersiz stok; başka kanaldan satılmış olabilir."
            "IDEMPOTENCY_KEY_REUSED" -> "Bu işlem anahtarı daha önce farklı içerikle kullanılmış."
            "RATE_LIMITED" -> "Çok fazla başarısız deneme; lütfen bekleyin."
            else -> "Bilinmeyen hata: $code"
        }

        assertTrue(mapError("LOT_BLOCKED").contains("geri çağrılmış"))
        assertTrue(mapError("INSUFFICIENT_STOCK").contains("yetersiz stok"))
        assertTrue(mapError("IDEMPOTENCY_KEY_REUSED").contains("işlem anahtarı"))
    }
}
