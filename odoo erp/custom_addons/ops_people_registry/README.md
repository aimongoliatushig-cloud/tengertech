# Хотын ажиллагаа: Ажилтан ба эрхийн бүртгэл

Энэ module нь Odoo 19 Community дээр хэрэглэгч, employee, алба нэгж, албан тушаал, системийн эрхийн мэдээллийг production-ready байдлаар нэгтгэнэ.

## Гол боломж

- `Алба нэгж`, `Албан тушаал`, `Системийн эрх`, `Шууд удирдлага`, `Ажилтны код` гэсэн ойлголтыг тусад нь хадгална.
- `res.users` болон `hr.employee` хооронд хоёр чиглэлийн sync хийнэ.
- Стандарт department/job master-ийг idempotent байдлаар үүсгэж, нэршлийг normalize хийнэ.
- Системийн эрхийг `ops.access.profile` + `res.groups` дээр суурилуулна.
- Existing user устгахгүйгээр employee link, department, job, access profile enrichment хийнэ.
- Суурь утасны жагсаалт болон CSV import-оор update/migration ажиллуулна.
- Audit report дээр unresolved mapping, missing link, duplicate master-уудыг жагсаана.

## Суулгах дараалал

1. `ops_people_registry` module-ийг update addons path дотор байршуулна.
2. Apps цэснээс module-ийг install хийнэ.
3. Install хийхэд post-init hook стандарт department/job/access profile болон суурь sync-ийг эхлүүлнэ.
4. Дараа нь `Хүний нөөц -> Тохиргоо -> Ажилтан бүртгэл` цэснээс:
   - `Суурь синк хийх`
   - эсвэл `CSV импорт хийх`
   - эсвэл `Аудитын тайлан`
   дарааллаар ажиллуулна.

## Ашиглах заавар

- `Системийн эрхийн профайл` дээр access profile-уудыг харж, зөвхөн authorized HR/Admin засна.
- `Users` жагсаалт дээр `Алба нэгж`, `Албан тушаал`, `Системийн эрх`, `Шууд удирдлага`, `Идэвхтэй` баганууд харагдана.
- `Employees` жагсаалт дээр `Ажилтны код`, `Алба нэгж`, `Албан тушаал`, `Системийн хэрэглэгч`, `Системийн эрх`, `Утас`, `Менежер` баганууд харагдана.
- CSV update хийхдээ `static/templates/employee_import_template.csv` загварыг ашиглана.
- Audit JSON жишээг `examples/mapping_report_example.json` файлаас харж болно.

## Config параметр

- `ops_people_registry.employee_code_prefix`
  - default: `HT`
- `ops_people_registry.archive_user_with_employee`
  - default: `False`
  - `True` бол employee archive хийхэд хэрэглэгчийн active төлөв дагаж өөрчлөгдөнө.

## Анхаарах зүйл

- Давхардсан department/job/employee илэрвэл module автоматаар устгахгүй, audit report-оор гаргана.
- `ops_user_type` талбар backward compatibility зориулалтаар хадгалагдсан ч UI дээр үндсэн ойлголт нь `Системийн эрх` байна.
- `people_directory.json` seed source нь суурь migration-д ашиглагдана.
