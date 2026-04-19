# Review checklist

## Бүтцийн шалгалт
- [x] `AGENTS.md` нэмсэн
- [x] `/docs` дотор role, workflow, mobile UX, review checklist нэмсэн
- [x] `municipal_project_mobile` addon үүсгэсэн
- [x] Manifest, models, views, security, assets бүрдсэн

## UX шалгалт
- [x] Dashboard дээр role-based summary байна
- [x] Manager screen дээр stat button ашигласан
- [x] Task form дээр sticky action bar оруулсан
- [x] Kanban card-уудыг mobile-friendly болгосон
- [x] Worker write action аваагүй

## Олдсон асуудал ба сайжруулалт
1. Header button дангаараа байвал mobile дээр доош гүйлгэхэд алга болдог.
   - Засвар: task/project form дээр sticky action bar нэмсэн.
2. Team leader screen дээр тайлан, явц, зураг нэг дор будилж болзошгүй байсан.
   - Засвар: form-ийг `Ерөнхий мэдээлэл / Ажлын явц / Зураг / Шийдвэр` гэсэн хэсгүүдэд хуваасан.
3. Dashboard ерөнхий ERP list шиг харагдах эрсдэлтэй байсан.
   - Засвар: stat button + intro card + preview list бүтэц ашигласан.
4. Worker дээр илүүц edit боломж гарч болзошгүй байсан.
   - Засвар: access болон rule-ийг read-only болгосон.
5. Base Odoo chatter mobile дэлгэцийг хэт урт болгож, англи систем текст гаргах эрсдэлтэй байсан.
   - Засвар: project болон task form-оос chatter-ийг хассан.
6. Menu action тус бүр custom mobile view-ээ тогтвортой ашиглахгүй эрсдэлтэй байсан.
   - Засвар: act_window view mapping-ийг menu action бүр дээр explicit болгосон.

## Дараагийн сайжруулалт
- Photo upload-ийг native camera intent-тэй ойртуулах
- Push notification нэмэх
- Offline draft sync хийх
- Dashboard дээр trend chart нэмэх
