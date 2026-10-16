// electron-builder `afterPack` hook: Windows .exe ichiga logo va versiya
// ma'lumotini yozadi. Odatda buni rcedit qiladi, lekin u Linux'da wine talab
// qiladi (`signAndEditExecutable: false` — rcedit o'chiq). `resedit` sof JS,
// shuning uchun installer istalgan tizimda logo bilan yig'iladi.
const fs = require('fs');
const path = require('path');

const RT_GROUP_ICON = 14;

exports.default = async function afterPack(context) {
  if (context.electronPlatformName !== 'win32') return;

  const { NtExecutable, NtExecutableResource, Resource, Data } = await import('resedit');
  const { appInfo } = context.packager;
  const exePath = path.join(context.appOutDir, `${appInfo.productFilename}.exe`);
  const iconPath = path.join(context.packager.projectDir, 'public/static-images/icon.ico');

  const exe = NtExecutable.from(fs.readFileSync(exePath), { ignoreCert: true });
  const res = NtExecutableResource.from(exe);

  // Electron'ning standart belgisi turgan guruh(lar)ni logo bilan almashtiramiz
  const icon = Data.IconFile.from(fs.readFileSync(iconPath));
  const groups = res.entries.filter((entry) => entry.type === RT_GROUP_ICON);
  if (groups.length === 0) throw new Error(`${exePath}: ikon guruhi topilmadi`);
  for (const group of groups) {
    Resource.IconGroupEntry.replaceIconsForResource(
      res.entries, group.id, group.lang, icon.icons.map((item) => item.data),
    );
  }

  // Fayl xususiyatlari (Windows "Свойства → Подробно")
  const [version] = Resource.VersionInfo.fromEntries(res.entries);
  const lang = version.getAllLanguagesForStringValues()[0] || { lang: 1033, codepage: 1200 };
  const [major, minor, patch] = appInfo.version.split('.').map(Number);
  version.setFileVersion(major, minor, patch, 0, lang.lang);
  version.setProductVersion(major, minor, patch, 0, lang.lang);
  version.setStringValues(lang, {
    ProductName: appInfo.productName,
    FileDescription: appInfo.productName,
    CompanyName: 'Avtotest tayyorlov',
    LegalCopyright: `© ${new Date().getFullYear()} Avtotest tayyorlov`,
    OriginalFilename: `${appInfo.productFilename}.exe`,
    InternalName: appInfo.productFilename,
    FileVersion: appInfo.version,
    ProductVersion: appInfo.version,
  });
  version.outputToResourceEntries(res.entries);

  res.outputResource(exe);
  fs.writeFileSync(exePath, Buffer.from(exe.generate()));
  console.log(`  • logo va versiya yozildi: ${path.basename(exePath)} (${groups.length} ikon guruhi)`);
};
