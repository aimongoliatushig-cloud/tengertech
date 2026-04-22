# Ажилтан бүртгэлийн админ гарын авлага

## Зорилго

Энэ шийдэл нь `Алба нэгж`, `Албан тушаал`, `Системийн эрх` гурвыг хооронд нь хольж ашиглахгүйгээр Odoo дээр хүний нөөцийн суурь мэдээллийг цэгцтэй болгоно.

## Гол ойлголт

- `Алба нэгж`: `hr.department`
- `Албан тушаал`: `hr.job`
- `Системийн эрх`: `ops.access.profile` + `res.groups`
- `Employee link`: `hr.employee.user_id`
- `Шууд удирдлага`: `hr.employee.parent_id`

## Өдөр тутмын ажиллагаа

1. Шинэ employee/user sync хийхдээ `Хүний нөөц -> Тохиргоо -> Ажилтан бүртгэл -> Суурь синк хийх` эсвэл `CSV импорт хийх` wizard ашиглана.
2. Wizard ажилласны дараа `Аудитын тайлан` руу орж unresolved мөрүүдийг шалгана.
3. Хэрэглэгчийн системийн эрхийг `Users` form дээр `Системийн эрх` талбараар удирдана.
4. Employee дээр department/job/manager солиход user form дээр автоматаар тусна.
5. User дээр access profile солиход profile group болон legacy ops user type автоматаар шинэчлэгдэнэ.
6. JSON тайлангийн жишээг `ops_people_registry/examples/mapping_report_example.json` файлаас авч ашиглаж болно.

## Импортын дүрэм

- Primary matching: `login`
- Department mapping: canonical Монгол нэрээр (`Удирдлага`, `Санхүүгийн алба` гэх мэт)
- Job mapping: canonical Монгол нэрээр (`Ерөнхий ня-бо`, `Мастер` гэх мэт)
- System role: profile нэрээр (`Захирал`, `Ерөнхий менежер`, `Санхүү`, `Ажилтан` гэх мэт)
- `active`: `1/0`, `true/false`, `идэвхтэй/идэвхгүй` форматаар болно

## Audit тайланг унших нь

- `Алба нэгж дутуу`: department mapping баталгаажаагүй
- `Албан тушаал дутуу`: job title normalization review шаардлагатай
- `Employee холбоос дутуу`: user дээр employee үүсээгүй эсвэл холбогдоогүй
- `Системийн эрх тодорхойгүй`: access profile гараар сонгох шаардлагатай
- `Шууд удирдлага тодорхойгүй`: manager chain review шаардлагатай
- `Давхардсан ...`: canonical master-аас гадуур давхар бичлэг байна

## Safety зарчим

- Existing user/delete хийхгүй
- Hard reset хийхгүй
- Duplicate master-ийг автоматаар устгахгүй
- Audit report review хийж байж archive/merge шийдвэр гаргана
