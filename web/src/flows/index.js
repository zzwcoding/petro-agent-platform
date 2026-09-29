// ===== 思考过程 v2：场景 key → 树路径叙事组件 全量注册表 =====
import { DataCleanFlow } from './dataClean.jsx'
import { FLOWS as StateBack } from './scenarios/stateBack.jsx'
import { FLOWS as StateGates } from './scenarios/stateGates.jsx'
import { FLOWS as Blocked } from './scenarios/blocked.jsx'
import { FLOWS as FrontChains } from './scenarios/frontChains.jsx'
import { FLOWS as ToolChains } from './scenarios/toolChains.jsx'
import { FLOWS as Direct } from './scenarios/direct.jsx'

export const FLOW_COMPS = {
  'data-clean': DataCleanFlow,
  ...StateBack,
  ...StateGates,
  ...Blocked,
  ...FrontChains,
  ...ToolChains,
  ...Direct,
}
