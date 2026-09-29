/**
 * api/sse 单测桩（P0-06：骨架＋单测桩，不接 A1）——
 * 覆盖：帧分发 / 保留三帧（done/error/replay_truncated）语义 /
 * 原生传输错误不 close（浏览器自动重连带 Last-Event-ID，00 §6.2 收场①）/
 * getLastEventId 断点帧号（A1 resume_run_id 续传接线点）。
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createEventStream } from './sse.js'

/** EventSource 测试桩：记录监听器，手工 emit 帧。 */
class FakeEventSource {
  constructor(url, opts) {
    this.url = url
    this.opts = opts
    this.listeners = {}
    this.onopen = null
    this.closed = false
    FakeEventSource.instances.push(this)
  }
  addEventListener(type, fn) {
    ;(this.listeners[type] = this.listeners[type] || []).push(fn)
  }
  emit(type, evt) {
    for (const fn of this.listeners[type] || []) fn(evt)
  }
  close() { this.closed = true }
}
FakeEventSource.instances = []

function frame(data, id = '7') {
  return { data: JSON.stringify(data), lastEventId: id }
}

beforeEach(() => {
  FakeEventSource.instances = []
})

describe('createEventStream 帧分发', () => {
  it('业务帧按类型分发，onFrame 带回 {event,data,id}', () => {
    const onFrame = vi.fn()
    const stream = createEventStream('/api/chat/streams/run-1', {
      events: ['stage', 'answer'],
      onFrame,
      EventSourceImpl: FakeEventSource
    })
    const src = FakeEventSource.instances[0]
    src.emit('stage', frame({ stage: 'retrieve' }, '3'))
    src.emit('answer', frame({ kind: 'table' }, '4'))
    expect(onFrame).toHaveBeenCalledTimes(2)
    expect(onFrame).toHaveBeenCalledWith({ event: 'stage', data: { stage: 'retrieve' }, id: '3' })
    expect(onFrame).toHaveBeenLastCalledWith({ event: 'answer', data: { kind: 'table' }, id: '4' })
    expect(stream.getLastEventId()).toBe('4')
  })

  it('未声明的业务帧不监听；保留三帧无需声明恒内置', () => {
    const src = createEventStream('/s', { events: ['stage'], EventSourceImpl: FakeEventSource }).source
    expect(src.listeners.stage).toHaveLength(1)
    expect(src.listeners.answer).toBeUndefined()
    for (const t of ['done', 'error', 'replay_truncated']) {
      expect(src.listeners[t]).toHaveLength(1)
    }
  })

  it('data 非 JSON 时原样透传不抛', () => {
    const onFrame = vi.fn()
    createEventStream('/s', { events: ['stage'], onFrame, EventSourceImpl: FakeEventSource })
    FakeEventSource.instances[0].emit('stage', { data: 'plain-text', lastEventId: '1' })
    expect(onFrame).toHaveBeenCalledWith({ event: 'stage', data: 'plain-text', id: '1' })
  })
})

describe('保留三帧语义（00 册 §6）', () => {
  it('done 帧：回调后 close', () => {
    const onDone = vi.fn()
    const stream = createEventStream('/s', { onDone, EventSourceImpl: FakeEventSource })
    const src = FakeEventSource.instances[0]
    src.emit('done', { data: '{}', lastEventId: '9' })
    expect(onDone).toHaveBeenCalledTimes(1)
    expect(src.closed).toBe(true)
    expect(stream.getLastEventId()).toBe('9')
  })

  it('服务端 error 帧（带 data）：回调错误包后 close——异常帧发出后关流', () => {
    const onError = vi.fn()
    createEventStream('/s', { onError, EventSourceImpl: FakeEventSource })
    const src = FakeEventSource.instances[0]
    src.emit('error', frame({ code: 'security_blocked', message: '命中平台规则' }, '8'))
    expect(onError).toHaveBeenCalledWith({ code: 'security_blocked', message: '命中平台规则' })
    expect(src.closed).toBe(true)
  })

  it('原生传输错误（无 data）：只观测不 close——收场①靠浏览器带 Last-Event-ID 自动重连', () => {
    const onNativeError = vi.fn()
    const onError = vi.fn()
    createEventStream('/s', { onNativeError, onError, EventSourceImpl: FakeEventSource })
    const src = FakeEventSource.instances[0]
    src.emit('error', { data: undefined, lastEventId: '' })
    expect(onNativeError).toHaveBeenCalledTimes(1)
    expect(onError).not.toHaveBeenCalled()
    expect(src.closed).toBe(false)
  })

  it('replay_truncated 帧：回调后 close（收场②/③，不静默丢帧）', () => {
    const onReplayTruncated = vi.fn()
    createEventStream('/s', { onReplayTruncated, EventSourceImpl: FakeEventSource })
    const src = FakeEventSource.instances[0]
    src.emit('replay_truncated', { data: '{}', lastEventId: '12' })
    expect(onReplayTruncated).toHaveBeenCalledTimes(1)
    expect(src.closed).toBe(true)
  })
})

describe('骨架边界', () => {
  it('close 幂等；无 EventSource 环境且未注入实现时显式报错', () => {
    const stream = createEventStream('/s', { EventSourceImpl: FakeEventSource })
    stream.close()
    stream.close()
    expect(FakeEventSource.instances[0].closed).toBe(true)
    expect(() => createEventStream('/s', { EventSourceImpl: undefined }))
      .toThrow('EventSource')
  })
})
