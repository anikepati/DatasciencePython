This is a modular, production-ready structure. I have separated the code into logical parts: **Data Layer**, **UI Components**, **Feature Modules**, and the **Main Layout**.

You can copy these into separate files in a React/Next.js project, or paste them into a single file if you are prototyping quickly.

###PrerequisiteInstall the icon library:
`npm install lucide-react clsx tailwind-merge`

---

###Part 1: Data Models & Mock Data (`data.ts`)This acts as the single source of truth for your mock enterprise data.

```typescript
// --- Types ---
export type ViewState = 'dashboard' | 'ingestion' | 'integration' | 'execution' | 'review' | 'reports';

export interface TaskLog {
  id: string;
  time: string;
  type: 'INFO' | 'WARN' | 'ERROR';
  source: 'SYS' | 'AUTH' | 'AGENT' | 'AI';
  msg: string;
}

export interface ExceptionItem {
  id: number;
  claimId: string;
  vendor: string;
  amount: string;
  status: 'Success' | 'Partial' | 'Failed' | 'Resolved';
  error: string | null;
  confidence: number;
  aiInsight?: string;
}

// --- Sample Data ---
export const MOCK_LOGS: TaskLog[] = [
  { id: '1', time: "10:14:01", type: "INFO", source: "SYS", msg: "Allocating pod in cluster 'us-east-1'..." },
  { id: '2', time: "10:14:02", type: "INFO", source: "AUTH", msg: "PingFederate: Token validated." },
  { id: '3', time: "10:14:04", type: "INFO", source: "AGENT", msg: "Navigating to https://portal.claims.com" },
  { id: '4', time: "10:14:05", type: "WARN", source: "AI", msg: "Selector ambiguity: Found 2 buttons matching 'Submit'." },
];

export const MOCK_EXCEPTIONS: ExceptionItem[] = [
  { id: 1045, claimId: "CLM-9921", vendor: "TechData", amount: "$500.00", status: "Success", error: null, confidence: 99 },
  { id: 1046, claimId: "CLM-9922", vendor: "Unk_Vendor", amount: "$120.00", status: "Partial", error: "Entity Extraction < 45%", confidence: 45, aiInsight: "Logo matched 'TechData' but OCR failed." },
  { id: 1047, claimId: "CLM-9923", vendor: "Microsoft", amount: "null", status: "Failed", error: "Validation: Amount Required", confidence: 0, aiInsight: "Field obscured by popup." },
  { id: 1048, claimId: "CLM-9924", vendor: "Google", amount: "$150.00", status: "Success", error: null, confidence: 98 },
  { id: 1049, claimId: "CLM-9925", vendor: "AWS", amount: "$12.50", status: "Failed", error: "Timeout: 404 URL", confidence: 0, aiInsight: "URL pattern changed." },
];

```

---

###Part 2: Shared UI Components (`components/ui.tsx`)Reusable building blocks to ensure a consistent "Enterprise" look.

```tsx
import React from 'react';
import { AlertTriangle, CheckCircle, XCircle, Activity, Loader2 } from 'lucide-react';

export const Badge = ({ status, text }: { status: string, text?: string }) => {
  const styles: Record<string, string> = {
    'Running': 'bg-blue-100 text-blue-700',
    'Success': 'bg-green-100 text-green-700',
    'Resolved': 'bg-green-100 text-green-700',
    'Failed': 'bg-red-100 text-red-700',
    'Partial': 'bg-yellow-100 text-yellow-800',
    'Low Conf': 'bg-yellow-100 text-yellow-800',
  };
  const safeStatus = styles[status] ? status : 'Partial';
  
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[safeStatus]}`}>
      {text || status}
    </span>
  );
};

export const MetricCard = ({ title, value, sub, icon, alert, onClick }: any) => (
  <div onClick={onClick} className={`bg-white p-5 rounded-xl border shadow-sm flex justify-between cursor-pointer transition-all ${alert ? 'border-red-200 bg-red-50/20 hover:border-red-400' : 'border-slate-200 hover:border-blue-300'}`}>
    <div>
      <p className="text-slate-500 text-sm font-medium">{title}</p>
      <h3 className="text-2xl font-bold text-slate-800 mt-1">{value}</h3>
      <p className={`text-xs mt-1 ${alert ? 'text-red-600 font-bold' : 'text-slate-400'}`}>{sub}</p>
    </div>
    <div className={`p-2 rounded-lg h-fit ${alert ? 'bg-red-100' : 'bg-slate-100'}`}>{icon}</div>
  </div>
);

export const StatusIcon = ({ status }: { status: string }) => {
  if (status === 'Success') return <CheckCircle size={16} className="text-green-600" />;
  if (status === 'Failed') return <XCircle size={16} className="text-red-600" />;
  if (status === 'Partial') return <AlertTriangle size={16} className="text-yellow-600" />;
  return <Activity size={16} className="text-slate-400" />;
};

```

---

###Part 3: Feature Modules (`components/modules/`)####3A. Ingestion Engine (SOP Upload)```tsx
import { useState, useEffect } from 'react';
import { FileVideo, RefreshCw, CheckCircle } from 'lucide-react';

export const IngestionModule = () => {
  const [step, setStep] = useState(0);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (step === 1) {
      const interval = setInterval(() => setProgress(p => p < 100 ? p + 2 : 100), 100);
      return () => clearInterval(interval);
    }
  }, [step]);

  return (
    <div className="max-w-4xl mx-auto bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex justify-between items-center">
        <h2 className="font-bold text-slate-800">SOP Ingestion Pipeline</h2>
        <div className="flex gap-2">
           {[1,2,3].map(i => <div key={i} className={`h-1.5 w-8 rounded-full ${step >= i-1 ? 'bg-blue-600' : 'bg-slate-200'}`}></div>)}
        </div>
      </div>

      <div className="p-8 min-h-[400px] flex flex-col justify-center">
        {step === 0 && (
          <div onClick={() => setStep(1)} className="border-2 border-dashed border-slate-300 rounded-xl p-12 flex flex-col items-center justify-center cursor-pointer hover:bg-slate-50 hover:border-blue-400 transition-all group">
            <div className="bg-blue-50 p-4 rounded-full mb-4 group-hover:scale-110 transition-transform"><FileVideo className="text-blue-600 w-8 h-8"/></div>
            <h3 className="text-lg font-medium text-slate-800">Drag SOP Video or Click to Browse</h3>
            <p className="text-sm text-slate-500 mt-2">Supports MP4, MKV. Max size 500MB.</p>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-3"><RefreshCw className="animate-spin text-blue-600"/><h3 className="font-bold text-slate-800">Processing...</h3></div>
              <span className="text-sm font-mono text-slate-500">Trace: ing-8821</span>
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden"><div className="h-full bg-blue-600 transition-all" style={{ width: `${progress}%` }}></div></div>
            <div className="bg-slate-900 rounded-lg p-4 font-mono text-xs text-green-400 h-48 overflow-y-auto">
               <div>[10:14:00] UPLOAD: Chunk 1/45 received (S3 bucket: raw-sop-landing)</div>
               <div>[10:14:01] KAFKA: Event published to topic 'sop-ingest'</div>
               {progress > 40 && <div>[10:14:04] AI_ENGINE: Gemini 1.5 Pro initialized.</div>}
               {progress > 70 && <div>[10:14:08] SCHEMA: Mapping form fields [Name, Email, ID].</div>}
               {progress === 100 && <div className="text-yellow-400">[10:14:15] SUCCESS: Config generated.</div>}
            </div>
          </div>
        )}
        
        {step === 1 && progress === 100 && (
           <div className="flex flex-col items-center pt-8 gap-4">
              <CheckCircle size={48} className="text-green-500" />
              <h3 className="text-xl font-bold">Ingestion Complete</h3>
              <button onClick={() => setStep(0)} className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700">Upload Another</button>
           </div>
        )}
      </div>
    </div>
  );
}

```

####3B. Integrations (Data Mapping)```tsx
import { FileSpreadsheet, ArrowRight, Save } from 'lucide-react';

export const IntegrationModule = () => {
  return (
    <div className="flex h-full gap-6">
      <div className="flex-1 bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col">
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50"><h3 className="font-bold text-slate-800">Source Configuration</h3></div>
        <div className="p-6 space-y-4">
          <div className="p-4 border border-blue-200 bg-blue-50 rounded-lg flex gap-3">
             <FileSpreadsheet className="text-blue-600 mt-1" />
             <div><h4 className="font-semibold text-blue-900">SharePoint Excel</h4><p className="text-xs text-blue-700">Auth: PingFederate (Active)</p></div>
          </div>
          <div className="space-y-2">
             <h4 className="text-xs font-bold uppercase text-slate-500 tracking-wider mb-2">Source Columns</h4>
            {['Invoice_ID', 'Vendor_Name', 'Total_Amt', 'Due_Date'].map(c => (
              <div key={c} className="flex justify-between p-3 bg-slate-50 border rounded text-sm hover:border-blue-300 cursor-grab active:cursor-grabbing"><span className="font-mono text-slate-700">{c}</span><span className="w-2 h-2 rounded-full bg-green-500"></span></div>
            ))}
          </div>
        </div>
      </div>
      <div className="flex flex-col items-center justify-center gap-2 text-slate-300">
         <ArrowRight size={32}/>
      </div>
      <div className="flex-1 bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col">
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex justify-between">
           <h3 className="font-bold text-slate-800">Agent Schema Map</h3>
           <span className="text-xs bg-slate-200 px-2 py-1 rounded text-slate-600">Template: Finance_Std_v1</span>
        </div>
        <div className="p-6 space-y-3">
           <MappingRow s="Invoice_ID" d="case_id" />
           <MappingRow s="Vendor_Name" d="vendor_name" />
           <MappingRow s="Total_Amt" d="amount_usd" />
           <MappingRow s="Due_Date" d="due_date" optional />
           
           <div className="mt-8 pt-4 border-t border-slate-100">
              <div className="flex items-center gap-2 mb-4">
                 <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                 <span className="text-sm text-slate-600">Save as reusable template</span>
              </div>
              <button className="w-full py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center justify-center gap-2">
                 <Save size={16}/> Save Integration
              </button>
           </div>
        </div>
      </div>
    </div>
  );
}

const MappingRow = ({s, d, optional}: any) => (
  <div className="flex items-center gap-2">
    <div className="flex-1 p-2 bg-slate-100 rounded border border-slate-200 text-xs font-mono text-slate-600">{s}</div>
    <ArrowRight size={12} className="text-slate-400"/>
    <div className={`flex-1 p-2 bg-white rounded border text-xs font-mono flex justify-between ${optional ? 'border-dashed border-slate-300 text-slate-400' : 'border-blue-300 text-blue-800'}`}>
       <span>{d}</span>
       {optional && <span className="text-[10px] uppercase">Opt</span>}
    </div>
  </div>
);

```

####3C. Execution (Live Command Center)```tsx
import { useState, useEffect } from 'react';
import { RefreshCw, Pause, X, Terminal, Cpu } from 'lucide-react';
import { MOCK_LOGS } from '../data'; // Assume imported from data file or same file

export const ExecutionModule = () => {
  const [logs, setLogs] = useState(MOCK_LOGS);
  
  useEffect(() => {
    const i = setInterval(() => setLogs(p => [...p.slice(-6), {id: Date.now().toString(), time: new Date().toLocaleTimeString(), type: "INFO", source: "AGENT", msg: `Processing Row #${Math.floor(Math.random()*100)}...`}]), 2000);
    return () => clearInterval(i);
  }, []);

  return (
    <div className="h-full flex flex-col gap-4">
      <div className="bg-white p-4 rounded-xl border border-slate-200 flex justify-between items-center shadow-sm">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 bg-blue-50 text-blue-600 rounded-lg flex items-center justify-center"><RefreshCw className="animate-spin"/></div>
          <div><h2 className="font-bold text-slate-800">Task #1094: Invoice_Bot_v2</h2><p className="text-xs text-slate-500">Running (Headless) • OpenShift Pod: worker-4a • Trace: tx-9981</p></div>
        </div>
        <div className="flex gap-2">
          <button className="flex items-center gap-2 px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-sm"><Pause size={14}/> Pause</button>
          <button className="flex items-center gap-2 px-3 py-2 bg-red-50 hover:bg-red-100 text-red-700 rounded text-sm"><X size={14}/> Stop</button>
        </div>
      </div>
      <div className="flex-1 flex gap-4 min-h-0">
        {/* Headless View */}
        <div className="flex-1 bg-slate-900 rounded-xl overflow-hidden flex flex-col border border-slate-700 shadow-lg">
           <div className="bg-slate-800 px-4 py-2 border-b border-slate-700 flex justify-between"><span className="text-xs text-slate-400 font-mono">VNC Stream (Headless)</span><div className="flex gap-1"><div className="w-2 h-2 rounded-full bg-green-500"></div></div></div>
           <div className="flex-1 bg-white p-8 flex items-center justify-center relative">
              <div className="w-full h-full bg-slate-50 border shadow-inner p-4 relative">
                  <div className="absolute top-1/2 left-1/2 w-4 h-4 bg-red-500/50 rounded-full animate-ping"></div>
                  <div className="h-8 bg-blue-600 w-32 rounded"></div>
                  <div className="absolute bottom-2 right-2 bg-black/70 text-white text-[10px] px-2 py-1 rounded">Action: Click(Submit)</div>
              </div>
           </div>
        </div>
        {/* Logs */}
        <div className="w-1/3 flex flex-col gap-4">
           <div className="flex-1 bg-white rounded-xl border border-slate-200 flex flex-col shadow-sm">
             <div className="px-4 py-2 bg-purple-50 border-b border-purple-100 flex gap-2"><Cpu size={14} className="text-purple-600"/><h4 className="font-bold text-xs text-purple-900">Arize AX (AI Trace)</h4></div>
             <div className="p-3 text-xs space-y-3 overflow-y-auto">
                <div className="border-l-2 border-purple-300 pl-2">
                  <div className="font-semibold text-slate-700">Step: Extract Amount</div>
                  <div className="text-slate-500">"Found $500.00 in .total-row" (Conf: 99%)</div>
                </div>
                <div className="border-l-2 border-purple-300 pl-2">
                  <div className="font-semibold text-slate-700">Step: Identify Button</div>
                  <div className="text-slate-500">"Submit button obscured by modal"</div>
                  <div className="text-purple-600 font-mono text-[10px] mt-1">Action: Close Modal</div>
                </div>
             </div>
           </div>
           <div className="flex-1 bg-slate-900 rounded-xl border border-slate-800 flex flex-col shadow-sm">
              <div className="px-4 py-2 bg-slate-800 border-b border-slate-700 flex gap-2"><Terminal size={14} className="text-slate-400"/><h4 className="font-bold text-xs text-slate-300">Splunk Stream</h4></div>
              <div className="p-3 font-mono text-[10px] space-y-1 overflow-y-auto">
                {logs.map((l,i)=><div key={i} className="flex gap-2"><span className="text-slate-500">{l.time}</span><span className="text-green-400">{l.msg}</span></div>)}
              </div>
           </div>
        </div>
      </div>
    </div>
  )
}

```

####3D. Resolution Desk (Review & HITL)```tsx
import { useState } from 'react';
import { Layers, RefreshCw, Filter, ChevronRight, AlertTriangle, X, Zap, CheckSquare, Edit3 } from 'lucide-react';
import { MOCK_EXCEPTIONS, ExceptionItem } from '../data';
import { Badge } from '../ui';

export const ResolutionModule = () => {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [items, setItems] = useState<ExceptionItem[]>(MOCK_EXCEPTIONS);
  const selectedItem = items.find(i => i.id === selectedId);

  const handleFix = () => {
    setItems(items.map(i => i.id === selectedId ? { ...i, status: 'Resolved', error: null } : i));
    setSelectedId(null);
  };

  return (
    <div className="h-full flex flex-col gap-6">
       {/* Top Bar */}
       <div className="bg-white border border-slate-200 p-4 rounded-xl flex justify-between items-center shadow-sm">
          <div className="flex items-center gap-4">
             <div className="p-3 bg-red-50 text-red-600 rounded-lg"><AlertTriangle size={24}/></div>
             <div><h2 className="text-lg font-bold text-slate-800">Task #1093: Claims Processing</h2><p className="text-sm text-slate-500">Status: Partial Success (82%) • 3 Items Failed</p></div>
          </div>
          <div className="flex gap-2">
            <button className="flex items-center gap-2 px-3 py-2 bg-white border border-slate-300 text-slate-700 rounded-lg text-sm hover:bg-slate-50"><Layers size={16}/> Group Similar (3)</button>
            <button className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 shadow-sm"><RefreshCw size={16}/> Rerun All</button>
          </div>
       </div>

       {/* Split Pane View */}
       <div className="flex-1 flex gap-6 min-h-0">
          
          {/* LEFT: Master List */}
          <div className="flex-1 bg-white rounded-xl border border-slate-200 overflow-hidden flex flex-col shadow-sm">
             <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 flex justify-between items-center">
                <h3 className="font-bold text-slate-700 text-sm">Exception Queue</h3>
                <div className="flex gap-2 text-xs text-slate-500 cursor-pointer"><Filter size={14}/> Filter: All</div>
             </div>
             <div className="overflow-y-auto flex-1">
                <table className="w-full text-sm text-left">
                  <thead className="bg-slate-50 text-slate-500 font-medium border-b border-slate-100">
                    <tr><th className="px-4 py-3">ID</th><th className="px-4 py-3">Claim</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Action</th></tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {items.map(item => (
                      <tr key={item.id} className={`hover:bg-blue-50 cursor-pointer ${selectedId === item.id ? 'bg-blue-50 ring-1 ring-inset ring-blue-200' : ''}`} onClick={() => setSelectedId(item.id)}>
                        <td className="px-4 py-3 font-mono text-xs text-slate-500">#{item.id}</td>
                        <td className="px-4 py-3 font-medium text-slate-800">{item.claimId}</td>
                        <td className="px-4 py-3"><Badge status={item.status} /></td>
                        <td className="px-4 py-3"><ChevronRight size={16} className="text-slate-300"/></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
             </div>
          </div>

          {/* RIGHT: Detail/Fix Panel */}
          <div className="w-[450px] bg-white rounded-xl border border-slate-200 overflow-hidden flex flex-col shadow-lg transition-all">
             {selectedItem ? (
               <>
                 <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex justify-between items-center">
                    <div>
                      <h3 className="font-bold text-slate-800">Resolve Item #{selectedItem.id}</h3>
                      <p className="text-xs text-red-500 flex items-center gap-1 mt-1"><AlertTriangle size={12}/> {selectedItem.error || "Review Required"}</p>
                    </div>
                    <button onClick={() => setSelectedId(null)}><X size={18} className="text-slate-400"/></button>
                 </div>
                 
                 <div className="p-6 flex-1 overflow-y-auto space-y-6">
                    <div className="space-y-2">
                       <h4 className="text-xs font-bold text-slate-500 uppercase">Snapshot Evidence</h4>
                       <div className="bg-slate-100 border border-slate-300 rounded h-32 flex items-center justify-center text-slate-400 text-xs shadow-inner">
                          [ PDF PREVIEW OF {selectedItem.claimId} ]
                       </div>
                    </div>

                    <div className="space-y-3">
                       <h4 className="text-xs font-bold text-slate-500 uppercase">Correct Data</h4>
                       <div><label className="text-xs text-slate-500">Vendor</label><input type="text" defaultValue={selectedItem.vendor} className="w-full border rounded p-2 text-sm font-medium focus:ring-2 focus:ring-blue-500 outline-none"/></div>
                       <div><label className="text-xs text-slate-500">Amount</label><input type="text" defaultValue={selectedItem.amount === "null" ? "" : selectedItem.amount} placeholder="0.00" className={`w-full border rounded p-2 text-sm font-medium ${selectedItem.amount === "null" ? "border-red-300 bg-red-50" : ""}`}/></div>
                    </div>

                    <div className="bg-purple-50 p-3 rounded-lg border border-purple-100">
                       <div className="flex items-center gap-2 text-purple-700 text-xs font-bold mb-1"><Zap size={12}/> AI Insight (Arize)</div>
                       <p className="text-xs text-purple-900">{selectedItem.aiInsight || `Confidence: ${selectedItem.confidence}%`}</p>
                       <label className="flex items-center gap-2 mt-2 text-xs text-purple-800 cursor-pointer"><input type="checkbox" className="accent-purple-600"/> Flag for retraining (RLHF)</label>
                    </div>
                 </div>

                 <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-end gap-3">
                    <button onClick={() => setSelectedId(null)} className="px-4 py-2 text-slate-600 hover:text-slate-800 text-sm">Skip</button>
                    <button onClick={handleFix} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium shadow-sm flex items-center gap-2"><CheckSquare size={16}/> Save & Fix</button>
                 </div>
               </>
             ) : (
               <div className="flex-1 flex flex-col items-center justify-center text-slate-400 p-8 text-center">
                  <Edit3 size={48} className="mb-4 text-slate-200"/>
                  <h3 className="text-slate-600 font-medium">Select an Exception</h3>
                  <p className="text-sm">Click a row on the left to review evidence and apply fixes.</p>
               </div>
             )}
          </div>
       </div>
    </div>
  );
}

```

---

###Part 4: Main Layout (`App.tsx` or `page.tsx`)Connects all modules.

```tsx
"use client";

import React, { useState } from 'react';
import { LayoutDashboard, Database, PlayCircle, Activity, Upload, BarChart, LogOut, ChevronRight, CheckCircle, Cpu, AlertTriangle } from 'lucide-react';
import { ViewState } from './data'; // Assume imported
import { MetricCard, Badge } from './components/ui';
import { IngestionModule } from './components/modules/ingestion'; // Assume paths
import { IntegrationModule } from './components/modules/integration';
import { ExecutionModule } from './components/modules/execution';
import { ResolutionModule } from './components/modules/resolution';

export default function AutoAgentEnterprise() {
  const [currentView, setCurrentView] = useState<ViewState>('dashboard');
  const [alerts, setAlerts] = useState(3);

  // Simple Dashboard Component (defined locally for simplicity, can be modularized)
  const DashboardView = () => (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="grid grid-cols-4 gap-4">
        <MetricCard title="Success Rate" value="98.2%" sub="+2.4% vs last week" icon={<CheckCircle className="text-green-500"/>} />
        <MetricCard title="Active Agents" value="12" sub="Currently Running" icon={<Cpu className="text-blue-500"/>} />
        <MetricCard title="Avg Latency" value="1.2s" sub="Per Step" icon={<Activity className="text-purple-500"/>} />
        <MetricCard title="Action Required" value="3" sub="Failed Tasks" alert icon={<AlertTriangle className="text-red-500"/>} onClick={() => setCurrentView('review')} />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50"><h3 className="font-semibold text-slate-800">Recent Activity</h3><button className="text-xs text-blue-600 font-medium hover:underline">View All</button></div>
        <table className="w-full text-sm text-left">
          <thead className="text-slate-500 font-medium border-b border-slate-100"><tr><th className="px-6 py-3">Task ID</th><th className="px-6 py-3">Agent</th><th className="px-6 py-3">Status</th><th className="px-6 py-3 text-right">Action</th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            <tr><td className="px-6 py-3 font-mono text-slate-500">#1094</td><td className="px-6 py-3">Invoice_Bot_v2</td><td className="px-6 py-3"><Badge status="Running"/></td><td className="px-6 py-3 text-right"><button className="text-blue-600" onClick={() => setCurrentView('execution')}>Monitor</button></td></tr>
            <tr><td className="px-6 py-3 font-mono text-slate-500">#1093</td><td className="px-6 py-3">Claims_Processor</td><td className="px-6 py-3"><Badge status="Partial"/></td><td className="px-6 py-3 text-right"><button className="text-blue-600" onClick={() => setCurrentView('review')}>Review</button></td></tr>
          </tbody>
        </table>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-slate-50 font-sans text-slate-800">
      <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col border-r border-slate-800">
        <div className="h-16 flex items-center px-6 border-b border-slate-800 gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-lg">A</div>
          <span className="font-bold text-white tracking-tight">AutoAgent Ent.</span>
        </div>
        <div className="flex-1 py-6 px-3 space-y-1">
          <NavItem icon={<LayoutDashboard size={18}/>} label="Dashboard" active={currentView === 'dashboard'} onClick={() => setCurrentView('dashboard')} />
          <NavItem icon={<Upload size={18}/>} label="Ingestion" active={currentView === 'ingestion'} onClick={() => setCurrentView('ingestion')} />
          <NavItem icon={<Database size={18}/>} label="Integrations" active={currentView === 'integration'} onClick={() => setCurrentView('integration')} />
          <NavItem icon={<PlayCircle size={18}/>} label="Execution" active={currentView === 'execution'} onClick={() => setCurrentView('execution')} />
          <div className="pt-4 pb-2 px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Operations</div>
          <NavItem icon={<Activity size={18}/>} label="Resolution Desk" active={currentView === 'review'} onClick={() => setCurrentView('review')} count={alerts} alert />
          <NavItem icon={<BarChart size={18}/>} label="Reports" active={false} />
        </div>
        <div className="p-4 border-t border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-xs text-white font-bold border border-slate-600">JD</div>
            <div className="flex-1 overflow-hidden"><p className="text-sm text-white truncate">John Doe</p><p className="text-xs text-slate-500 truncate">S. Admin</p></div>
            <LogOut size={16} className="text-slate-500 hover:text-white cursor-pointer" />
          </div>
        </div>
      </aside>

      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 shadow-sm z-10">
          <div className="flex items-center gap-2 text-sm text-slate-500"><span className="font-medium text-slate-800">Workspace</span> <ChevronRight size={14}/> <span className="capitalize">{currentView}</span></div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1 bg-green-50 text-green-700 rounded-full text-xs font-medium border border-green-200"><div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>System Healthy</div>
          </div>
        </header>
        <div className="flex-1 overflow-y-auto bg-slate-50/50 p-6">
          {currentView === 'dashboard' && <DashboardView />}
          {currentView === 'ingestion' && <IngestionModule />}
          {currentView === 'integration' && <IntegrationModule />}
          {currentView === 'execution' && <ExecutionModule />}
          {currentView === 'review' && <ResolutionModule />}
        </div>
      </main>
    </div>
  );
}

const NavItem = ({ icon, label, active, onClick, count, alert }: any) => (
  <button onClick={onClick} className={`w-full flex items-center justify-between px-3 py-2.5 rounded-md transition-all group ${active ? 'bg-slate-800 text-white shadow-md' : 'text-slate-400 hover:bg-slate-800/50 hover:text-white'}`}>
    <div className="flex items-center gap-3">{icon}<span className="text-sm font-medium">{label}</span></div>
    {count && <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${alert ? 'bg-red-500 text-white' : 'bg-slate-700 text-slate-300'}`}>{count}</span>}
  </button>
);

```
