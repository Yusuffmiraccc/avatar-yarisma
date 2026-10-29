package com.avatar.app

import com.avatar.app.domain.validator.SaleValidator
import org.junit.Assert.assertEquals
import org.junit.Test
import java.math.BigDecimal
import java.math.RoundingMode

class BigDecimalCalculationTest {

    @Test
    fun testCurrencyMultiplicationPrecision() {
        val qty = BigDecimal("85")
        val unitPrice = BigDecimal("24.00")
        val expected = BigDecimal("2040.00")
        val actual = SaleValidator.calculateLineTotal(qty, unitPrice)
        assertEquals(expected, actual)
    }

    @Test
    fun testReferenceScenarioEkpRounding() {
        // PDF Senaryosu: Toplam maliyet 1543.50, Miktar 85 paket
        val totalCost = BigDecimal("1543.50")
        val qty = BigDecimal("85")
        val exactEkp = totalCost.divide(qty, 4, RoundingMode.HALF_UP) // 18.1588
        assertEquals(BigDecimal("18.1588"), exactEkp)

        val displayEkp = exactEkp.setScale(2, RoundingMode.HALF_UP) // 18.16
        assertEquals(BigDecimal("18.16"), displayEkp)
    }

    @Test
    fun testGrandTotalSummation() {
        val line1 = SaleValidator.calculateLineTotal(BigDecimal("30"), BigDecimal("24.00")) // 720.00
        val line2 = SaleValidator.calculateLineTotal(BigDecimal("25"), BigDecimal("24.00")) // 600.00
        val line3 = SaleValidator.calculateLineTotal(BigDecimal("30"), BigDecimal("24.00")) // 720.00

        val grandTotal = SaleValidator.calculateGrandTotal(listOf(line1, line2, line3))
        assertEquals(BigDecimal("2040.00"), grandTotal)
    }

    @Test
    fun testFractionalQuantityLineTotalRounding() {
        // 3.125 kg x 11.50 € = 35.9375 € -> 35.94 € (ROUND_HALF_UP)
        val qty = BigDecimal("3.125")
        val price = BigDecimal("11.50")
        val total = SaleValidator.calculateLineTotal(qty, price)
        assertEquals(BigDecimal("35.94"), total)
    }
}
