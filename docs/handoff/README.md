# AVATAR — Kodlama LLM'i için teslim paketi

**Başlangıç:** `LLM_HANDOFF.md`  
**Doküman tabanı:** v1.45; devir dosyaları: v1.46  
**Mevcut backend:** başlangıç iskeleti, tam ürün değil.

## Kodlama LLM'ine verilecek dosyalar

Bu ZIP'in tamamını ver. İlk mesaj/prompt olarak `LLM_HANDOFF.md` dosyasının tamamını yapıştır veya dosya olarak göster ve “paketteki talimatlara göre uygula” de. LLM önce şu dosyaları okumalı:

1. `LLM_HANDOFF.md`
2. `AVATAR_MASTER_BRIEF.md`
3. `BACKEND_DATABASE_ARCHITECTURE_CLOSURE.md`
4. `DOCUMENT_INDEX.md`
5. `IMPLEMENTATION_PLAN.md`
6. `ACCEPTANCE_CRITERIA.md`
7. `KNOWN_GAPS.md`

Her görevde tüm tarihçe ciltlerini topluca okumak yerine `DOCUMENT_INDEX.md`'den ilgili kaynakları açsın.

## Güvenlik notu

Bu paket gerçek/production veritabanında işlem yapıldığını iddia etmez. Migration ve testler yalnızca izole lokal test ortamında çalıştırılabilir. Gerçek kimlik bilgilerini `.env.example` veya kaynak koda koyma.
