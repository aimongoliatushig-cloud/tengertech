# Municipal Procurement Workflow

`municipal_procurement_workflow` модуль нь төсөл, ажилбартай шууд холбоотой худалдан авалтын урсгалыг Odoo 19 Community дээр хэрэгжүүлнэ.

## Гол боломжууд

- Төсөл эсвэл ажилбараас худалдан авалтын хүсэлт үүсгэнэ.
- Хүсэлт бүр дээр хариуцсан няравыг заавал сонгоно.
- 3 үнийн санал, сонгосон нийлүүлэгч, босго дүнгийн дагуу low/high урсгал автоматаар ялгарна.
- High flow дээр бичиг хэрэг, захирал, гэрээний шат заавал мөрдөгдөнө.
- Санхүү, хүлээн авалт, аудитын түүх, chatter, activity дагалдана.
- Ерөнхий менежер төслөөр, няраваар, төлвөөр, хугацаагаар хянах самбартай.
- Тусдаа mobile-first web app нь Odoo JSON endpoint-оор холбогдоно.

## Файлын бүтэц

- `models/procurement_request.py`
  Худалдан авалтын үндсэн model, мөр, үнийн санал, баримт, аудит, project/task integration
- `controllers/procurement_api.py`
  Web app-д зориулсан аюулгүй JSON endpoint-ууд
- `security/`
  Group, access, record rule
- `views/`
  List, form, kanban, search, graph, pivot, project/task smart button
- `tests/test_procurement_workflow.py`
  Workflow, threshold, security, API smoke test

## Odoo суулгах

1. `municipal_procurement_workflow` хавтсыг custom addons path дотор үлдээнэ.
2. Odoo тохиргоонд addons path-д `custom_addons` орсон эсэхийг шалгана.
3. App жагсаалтыг шинэчилнэ.
4. `Худалдан авалтын удирдлага` модулийг install хийнэ.

Жишээ update/test command:

```powershell
& "C:\Users\User\Desktop\hot tohjilt\odoo erp\Odoo 19\python\python.exe" `
  "C:\Users\User\Desktop\hot tohjilt\odoo erp\odoo-bin" `
  -c "C:\path\to\odoo.conf" `
  -d your_database `
  -i municipal_procurement_workflow `
  --test-enable `
  --stop-after-init
```

## Web app тохиргоо

Web app нь Odoo login credential-ээ ашиглан procurement API руу холбогдоно.

Шаардлагатай env:

```env
ODOO_URL=http://localhost:8069
ODOO_DB=your_database
ODOO_LOGIN=admin
ODOO_PASSWORD=admin
```

Web app command:

```powershell
cd "C:\Users\User\Desktop\hot tohjilt\web app"
npm install
npm run dev
```

Production шалгалт:

```powershell
npm run lint
npm run build
```

## API endpoint-ууд

- `POST /mpw/api/login`
- `GET /mpw/api/me`
- `GET /mpw/api/meta`
- `GET /mpw/api/requests`
- `GET /mpw/api/requests/<id>`
- `POST /mpw/api/requests`
- `POST /mpw/api/requests/<id>/submit`
- `POST /mpw/api/requests/<id>/submit_quotations`
- `POST /mpw/api/requests/<id>/move_to_finance_review`
- `POST /mpw/api/requests/<id>/prepare_order`
- `POST /mpw/api/requests/<id>/director_decision`
- `POST /mpw/api/requests/<id>/attach_final_order`
- `POST /mpw/api/requests/<id>/mark_contract_signed`
- `POST /mpw/api/requests/<id>/mark_paid`
- `POST /mpw/api/requests/<id>/mark_received`
- `POST /mpw/api/requests/<id>/mark_done`
- `POST /mpw/api/requests/<id>/cancel`
- `POST /mpw/api/requests/<id>/upload_attachment`
- `GET /mpw/api/dashboard`

## Шалгасан зүйл

- Python compile алдаагүй
- XML parse алдаагүй
- `web app` дээр `npm run lint` амжилттай
- `web app` дээр `npm run build` амжилттай

## Анхаарах зүйл

- Low/high урсгал нь мөрөөр биш, сонгосон нэг нийлүүлэгчийн нийт дүнгээр тодорхойлогдоно.
- Low flow дээр санхүү supplier-аа сонгож төлбөр баталгаажуулж болно.
- Assigned жагсаалт нь зөвхөн нярав биш, `current_responsible_user_id` дээр тулгуурлана.
