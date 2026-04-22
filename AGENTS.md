# AGENTS.md

## Төслийн зорилго
- Энэ repo дээр хотын талбайн ажиллагаанд зориулсан Odoo болон web workspace хөгжүүлдэг.
- `municipal_project_mobile` модуль нь талбайн төслийн удирдлагыг mobile-first логикоор хэрэгжүүлнэ.

## Гол дүрэм
- End-user UI текстийг зөвхөн Монгол хэлээр бичнэ.
- ERP-style олон таб, хэт их талбар, давхар урсгалаас зайлсхийнэ.
- Нэг дэлгэц дээр нэг гол зорилго баримтална.
- Үйл ажиллагаа хариуцсан менежерт executive summary, багийн ахлагчид гүйцэтгэлийн урсгал, ажилтанд зөвхөн унших горим өгнө.

## Role hierarchy
1. Үйл ажиллагаа хариуцсан менежер
2. Төслийн менежер
3. Багийн ахлагч
4. Ажилтан

## Хөгжүүлэлтийн зарчим
- Odoo модуль install-ready байх.
- Security group, access, record rule гурав хоорондоо зөрчилдөхгүй байх.
- Mobile UX дээр kanban, stat button, sticky action bar-ийг түрүүлж ашиглах.
- Тайлангийн урсгал `ноорог -> илгээсэн -> баталсан/буцаасан` логиктой байна.

## Хүссэн файл бүтэц
- `/docs/roles.md`
- `/docs/workflow.md`
- `/docs/mobile-ux.md`
- `/docs/review-checklist.md`
- `odoo erp/custom_addons/municipal_project_mobile`

## Шалгах зүйл
- Module manifest болон XML ачаалж чадаж байна уу
- Python syntax алдаагүй юу
- UI label англи хэлгүй юу
- Worker write эрхгүй үлдсэн үү
- Team leader 3 товшилтоос дотроо нийтлэг ажлаа хийж чадаж байна уу
