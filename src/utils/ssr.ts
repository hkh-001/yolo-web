
import { provide } from 'vue'
import { ID_INJECTION_KEY, ZINDEX_INJECTION_KEY } from 'element-plus'

export function preventElemmentSSRError() {
    provide(ID_INJECTION_KEY, {
        prefix: 100,
        current: 0,
    })

    provide(ZINDEX_INJECTION_KEY, { current: 0 })
}