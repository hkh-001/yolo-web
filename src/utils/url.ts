export function setURLParams(params: Record<string, string | null>, replace: boolean = false) {
    const urlObj = new URL(window.location.href);
    for (const key in params) {
        if (params[key] === null) {
            urlObj.searchParams.delete(key);
        } else {
            urlObj.searchParams.set(key, params[key]);
        }
    }
    if (replace) window.history.replaceState({}, '', urlObj.toString());
    else window.history.pushState({}, '', urlObj.toString());
}