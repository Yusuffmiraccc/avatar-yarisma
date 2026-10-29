package com.avatar.app

import com.avatar.app.domain.barcode.BarcodeParser
import com.avatar.app.domain.barcode.BarcodeType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class BarcodeParserTest {

    @Test
    fun parse_plainLotCode_matchesSuccessfully() {
        val result = BarcodeParser.parse("SUC-2026-045")
        assertTrue(result.isValid)
        assertEquals(BarcodeType.LOT_CODE, result.type)
        assertEquals("SUC-2026-045", result.lotCode)
        assertNull(result.gtin)
    }

    @Test
    fun parse_lotUriPrefix_extractsLotCode() {
        val result = BarcodeParser.parse("avatar://lot/ET-2026-001")
        assertTrue(result.isValid)
        assertEquals(BarcodeType.LOT_CODE, result.type)
        assertEquals("ET-2026-001", result.lotCode)

        val resultPrefixed = BarcodeParser.parse("LOT:KUZU-BUT-001")
        assertTrue(resultPrefixed.isValid)
        assertEquals("KUZU-BUT-001", resultPrefixed.lotCode)
    }

    @Test
    fun parse_ean13Barcode_matchesProductGtin() {
        val result = BarcodeParser.parse("8690123456789")
        assertTrue(result.isValid)
        assertEquals(BarcodeType.PRODUCT_GTIN, result.type)
        assertEquals("8690123456789", result.gtin)
        assertNull(result.lotCode)
    }

    @Test
    fun parse_gs1DataMatrix_extractsLotAndGtin() {
        val gs1 = "(01)08690123456789(10)SUC-2026-045"
        val result = BarcodeParser.parse(gs1)
        assertTrue(result.isValid)
        assertEquals(BarcodeType.GS1_COMPLEX, result.type)
        assertEquals("SUC-2026-045", result.lotCode)
        assertEquals("08690123456789", result.gtin)
    }

    @Test
    fun parse_emptyOrInvalidInput_returnsError() {
        val nullResult = BarcodeParser.parse(null)
        assertFalse(nullResult.isValid)
        assertEquals(BarcodeType.UNKNOWN, nullResult.type)
        assertEquals("", nullResult.rawText)
        assertNotNull(nullResult.errorMessage)

        val blankResult = BarcodeParser.parse("   ")
        assertFalse(blankResult.isValid)
        assertEquals(BarcodeType.UNKNOWN, blankResult.type)
        assertNotNull(blankResult.errorMessage)

        val emptyResult = BarcodeParser.parse("")
        assertFalse(emptyResult.isValid)
        assertEquals(BarcodeType.UNKNOWN, emptyResult.type)
        assertNotNull(emptyResult.errorMessage)

        val invalidResult = BarcodeParser.parse("!!!invalid???")
        assertFalse(invalidResult.isValid)
        assertEquals(BarcodeType.UNKNOWN, invalidResult.type)
    }
}
