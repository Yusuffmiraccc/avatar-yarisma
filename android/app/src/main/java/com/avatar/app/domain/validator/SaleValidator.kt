package com.avatar.app.domain.validator

import com.avatar.app.data.local.entity.SellableLotEntity
import java.math.BigDecimal
import java.math.RoundingMode

sealed class ValidationResult {
    object Valid : ValidationResult()
    data class Invalid(val reason: String) : ValidationResult()
}

object SaleValidator {

    fun validateQuantity(quantity: BigDecimal?, availableOnHand: BigDecimal?): ValidationResult {
        if (quantity == null || quantity <= BigDecimal.ZERO) {
            return ValidationResult.Invalid("Miktar 0'dan büyük olmalıdır.")
        }
        if (availableOnHand != null && quantity > availableOnHand) {
            return ValidationResult.Invalid("Girilen miktar ($quantity) mevcut stoktan ($availableOnHand) fazladır.")
        }
        return ValidationResult.Valid
    }

    fun validateLotNotBlocked(lotId: Long, lotCode: String, blockedLotIds: Set<Long>, blockedLotCodes: Set<String>): ValidationResult {
        if (blockedLotIds.contains(lotId) || blockedLotCodes.contains(lotCode)) {
            return ValidationResult.Invalid("Lot $lotCode bloke edilmiştir / geri çağrılmıştır. Satışı yapılamaz!")
        }
        return ValidationResult.Valid
    }

    fun calculateLineTotal(quantity: BigDecimal, unitPrice: BigDecimal): BigDecimal {
        return (quantity * unitPrice).setScale(2, RoundingMode.HALF_UP)
    }

    fun calculateGrandTotal(lineTotals: List<BigDecimal>): BigDecimal {
        return lineTotals.fold(BigDecimal.ZERO) { acc, total -> acc + total }.setScale(2, RoundingMode.HALF_UP)
    }

    data class DraftLine(
        val lot: SellableLotEntity,
        val quantity: BigDecimal
    ) {
        val unitPrice: BigDecimal get() = lot.salePrice
        val lineTotal: BigDecimal get() = calculateLineTotal(quantity, unitPrice)
    }

    fun mergeDraftLines(lines: List<DraftLine>): List<DraftLine> {
        return lines.groupBy { it.lot.id }.map { (_, group) ->
            val totalQty = group.map { it.quantity }.reduce { acc, q -> acc + q }
            DraftLine(group.first().lot, totalQty)
        }
    }
}
