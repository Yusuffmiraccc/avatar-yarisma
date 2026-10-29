package com.avatar.app.domain.barcode

import java.util.regex.Pattern

enum class BarcodeType {
    LOT_CODE,
    PRODUCT_GTIN,
    GS1_COMPLEX,
    UNKNOWN
}

data class BarcodeScanResult(
    val rawText: String,
    val type: BarcodeType,
    val lotCode: String? = null,
    val gtin: String? = null,
    val isValid: Boolean = true,
    val errorMessage: String? = null
)

object BarcodeParser {

    private val LOT_URI_PATTERN = Pattern.compile("^(?:avatar://lot/|LOT:)(.+)$", Pattern.CASE_INSENSITIVE)
    private val LOT_CODE_PATTERN = Pattern.compile("^[A-Z0-9]{2,10}-[A-Z0-9]{2,10}-[0-9]{3,6}$", Pattern.CASE_INSENSITIVE)
    private val EAN13_PATTERN = Pattern.compile("^[0-9]{13}$")
    private val GS1_AI10_PATTERN = Pattern.compile("(?:\\(10\\)|10)([A-Z0-9-]{3,30})", Pattern.CASE_INSENSITIVE)
    private val GS1_AI01_PATTERN = Pattern.compile("(?:\\(01\\)|01)([0-9]{14})")

    /**
     * Kamera veya harici Bluetooth lazer okuyucudan gelen ham metni ayrıştırır.
     */
    fun parse(rawInput: String?): BarcodeScanResult {
        if (rawInput.isNullOrBlank()) {
            return BarcodeScanResult(
                rawText = rawInput ?: "",
                type = BarcodeType.UNKNOWN,
                isValid = false,
                errorMessage = "Boş veya geçersiz barkod girdisi."
            )
        }

        val text = rawInput.trim()

        // 1. Doğrudan avatar://lot/ veya LOT: prefix kontrolü
        val uriMatcher = LOT_URI_PATTERN.matcher(text)
        if (uriMatcher.matches()) {
            val code = uriMatcher.group(1)?.trim() ?: ""
            return BarcodeScanResult(
                rawText = text,
                type = BarcodeType.LOT_CODE,
                lotCode = code,
                isValid = true
            )
        }

        // 2. GS1-128 veya GS1-DataMatrix / QR (AI 01 = GTIN, AI 10 = Lot No)
        val gs1LotMatcher = GS1_AI10_PATTERN.matcher(text)
        val gs1GtinMatcher = GS1_AI01_PATTERN.matcher(text)
        if (gs1LotMatcher.find() || gs1GtinMatcher.find()) {
            val lot = if (gs1LotMatcher.find(0)) gs1LotMatcher.group(1)?.trim() else null
            val gtin = if (gs1GtinMatcher.find(0)) gs1GtinMatcher.group(1)?.trim() else null
            return BarcodeScanResult(
                rawText = text,
                type = BarcodeType.GS1_COMPLEX,
                lotCode = lot,
                gtin = gtin,
                isValid = true
            )
        }

        // 3. Standart Lot Kodu (Örn: SUC-2026-045, ET-2026-001, KARKAS-2026-001)
        if (LOT_CODE_PATTERN.matcher(text).matches()) {
            return BarcodeScanResult(
                rawText = text,
                type = BarcodeType.LOT_CODE,
                lotCode = text.uppercase(),
                isValid = true
            )
        }

        // 4. Standart EAN-13 / Perakende Ürün Barkodu
        if (EAN13_PATTERN.matcher(text).matches()) {
            return BarcodeScanResult(
                rawText = text,
                type = BarcodeType.PRODUCT_GTIN,
                gtin = text,
                isValid = true
            )
        }

        // 5. Bilinmeyen veya desteklenmeyen format
        return BarcodeScanResult(
            rawText = text,
            type = BarcodeType.UNKNOWN,
            isValid = false,
            errorMessage = "Desteklenmeyen barkod formatı: $text"
        )
    }
}
