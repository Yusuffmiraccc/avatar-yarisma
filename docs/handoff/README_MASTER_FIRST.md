# AVATAR dokümantasyonu — LLM kullanım kuralı

**Önce `AVATAR_MASTER_BRIEF.md` dosyasını oku.** Olağan görevlerde 43 cildin tamamını LLM bağlamına yükleme. Master brief yeterliyse orada dur; değilse sadece ilgili kaynak dosyayı aç. `volumes/` ve `manifests/` altındaki eski sürümler denetim arşividir.

Bu paket eski ciltleri silmez; geçmiş ve izlenebilirlik için saklar. Günlük kodlama işlerinde token tüketimini azaltan dosya `AVATAR_MASTER_BRIEF.md`'dir.

**Önemli:** Master brief migration/DB onayı değildir. Alembic migration veya MySQL oluşturma/değiştirme için ayrı açık kullanıcı onayı gerekir.
