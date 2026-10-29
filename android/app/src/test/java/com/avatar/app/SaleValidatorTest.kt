package com.avatar.app

import com.avatar.app.data.local.entity.SellableLotEntity
import com.avatar.app.domain.validator.SaleValidator
import com.avatar.app.domain.validator.ValidationResult
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.math.BigDecimal

class SaleValidatorTest {

    @Test
    fun testQuantityMustBePositive() {
        val zeroResult = SaleValidator.validateQuantity(BigDecimal.ZERO, BigDecimal("100"))
        assertTrue(zeroResult is ValidationResult.Invalid)

        val negativeResult = SaleValidator.validateQuantity(BigDecimal("-5.00"), BigDecimal("100"))
        assertTrue(negativeResult is ValidationResult.Invalid)

        val positiveResult = SaleValidator.validateQuantity(BigDecimal("10.00"), BigDecimal("100"))
        assertEquals(ValidationResult.Valid, positiveResult)
    }

    @Test
    fun testQuantityCannotExceedOnHandStock() {
        val exceedResult = SaleValidator.validateQuantity(BigDecimal("105"), BigDecimal("100"))
        assertTrue(exceedResult is ValidationResult.Invalid)

        val exactResult = SaleValidator.validateQuantity(BigDecimal("100"), BigDecimal("100"))
        assertEquals(ValidationResult.Valid, exactResult)
    }

    @Test
    fun testBlockedLotIsRejectedImmediately() {
        val blockedIds = setOf(101L, 102L)
        val blockedCodes = setOf("ET-2026-001", "SUC-2026-045")

        val resultBlocked = SaleValidator.validateLotNotBlocked(102L, "SUC-2026-045", blockedIds, blockedCodes)
        assertTrue(resultBlocked is ValidationResult.Invalid)

        val resultAllowed = SaleValidator.validateLotNotBlocked(200L, "SUC-2026-099", blockedIds, blockedCodes)
        assertEquals(ValidationResult.Valid, resultAllowed)
    }

    @Test
    fun testMergeDraftLinesForSameLot() {
        val lot = SellableLotEntity(
            id = 1L,
            lotCode = "LOT-1",
            productId = 10L,
            productCode = "PROD-1",
            productName = "Ürün 1",
            onHandQuantity = BigDecimal("50"),
            unitCode = "PACK",
            expiryDate = null,
            locationCode = null,
            salePrice = BigDecimal("20.00")
        )

        val line1 = SaleValidator.DraftLine(lot, BigDecimal("10"))
        val line2 = SaleValidator.DraftLine(lot, BigDecimal("15"))

        val merged = SaleValidator.mergeDraftLines(listOf(line1, line2))
        assertEquals(1, merged.size)
        assertEquals(BigDecimal("25"), merged[0].quantity)
        assertEquals(BigDecimal("500.00"), merged[0].lineTotal)
    }
}
