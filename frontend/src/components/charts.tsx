// Palet chart: oranye (primer), charcoal, dan netral hangat.
import { ReactNode } from 'react'
import { ResponsiveContainer } from 'recharts'
export const C = { brand: '#E0560D', ink: '#23262B', amber: '#D9A441', stone: '#A8A29E', soft: '#F2B58A', green: '#2F8F6B' }
export const SERIES = [C.brand, C.ink, C.amber, C.stone, C.green]
export const axis = { stroke: '#A8A29E', fontSize: 12, tickLine: false, axisLine: false } as const
export const grid = { stroke: '#EDEBE7', strokeDasharray: '3 3', vertical: false } as const
export const tip = { contentStyle: { border: '1px solid #E5E4E0', borderRadius: 8, fontSize: 12, boxShadow: 'none' } }
export const Chart = ({ h = 240, children }: { h?: number; children: ReactNode }) => (
  <div style={{ height: h }}><ResponsiveContainer width="100%" height="100%">{children as any}</ResponsiveContainer></div>
)
