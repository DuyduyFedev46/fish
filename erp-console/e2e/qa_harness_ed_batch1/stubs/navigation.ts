export function useRouter() { return { push: (h: string) => { (window as any).__pushed = h; document.title = "pushed:" + h; } }; }
