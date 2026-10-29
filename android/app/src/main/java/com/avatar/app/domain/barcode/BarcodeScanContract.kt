package com.avatar.app.domain.barcode

interface IBarcodeScanner {
    fun isCameraAvailable(): Boolean
    fun parseBarcode(rawText: String): BarcodeScanResult
}

class DefaultBarcodeScanner(
    private val hasHardwareCamera: Boolean = true
) : IBarcodeScanner {

    override fun isCameraAvailable(): Boolean = hasHardwareCamera

    override fun parseBarcode(rawText: String): BarcodeScanResult {
        return BarcodeParser.parse(rawText)
    }
}
