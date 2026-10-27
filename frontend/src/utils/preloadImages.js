// Keyingi savollarning rasmlarini oldindan yuklaydi: savol almashganda rasm
// serverdan kutilmaydi, brauzer keshidan darhol chiqadi.
const requested = new Set();

export function preloadImages(items, mediaPath) {
  items.forEach((item) => {
    if (!item?.image) return;
    const src = mediaPath + item.image;
    if (requested.has(src)) return;
    requested.add(src);
    new Image().src = src;
  });
}
