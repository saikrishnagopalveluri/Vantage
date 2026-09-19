// No React imports: the root layout is a server component and inlines this before first paint,
// so a saved theme never flashes the wrong colours.
export const THEME_KEY = "vantage.theme";
export const THEME_BOOT_SCRIPT = `try{var t=localStorage.getItem('${THEME_KEY}');if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t)}catch(e){}`;
