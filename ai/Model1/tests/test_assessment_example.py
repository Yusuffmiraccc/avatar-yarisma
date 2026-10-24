def test_assessment_fason_example():
    et_maliyeti = 100 * 9.70
    baharat_maliyeti = 2 * 24.00
    bagirsak_maliyeti = 5 * 11.60
    fason_hizmet_maliyeti = 85 * 5.50

    toplam_maliyet = (
        et_maliyeti
        + baharat_maliyeti
        + bagirsak_maliyeti
        + fason_hizmet_maliyeti
    )
    ekp = toplam_maliyet / 85

    assert round(et_maliyeti, 2) == 970.00
    assert round(baharat_maliyeti, 2) == 48.00
    assert round(bagirsak_maliyeti, 2) == 58.00
    assert round(fason_hizmet_maliyeti, 2) == 467.50
    assert round(toplam_maliyet, 2) == 1543.50
    assert round(ekp, 2) == 18.16
