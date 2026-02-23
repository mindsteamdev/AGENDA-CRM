/* eslint-disable */
'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
    PieChart, Pie, Cell, Legend, BarChart, Bar
} from 'recharts';
import {
    BellIcon,
    CheckCircleIcon,
    ExclamationCircleIcon
} from "@heroicons/react/24/outline";

const COLORS = ['#5c1414', '#c5a059', '#2d1b1b', '#8b5e34', '#e6d5b8'];

export default function AdminPage() {
    const [metrics, setMetrics] = useState<any>(null); // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [trends, setTrends] = useState<any[]>([]); // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [distribution, setDistribution] = useState<any[]>([]); // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [revenue, setRevenue] = useState<number>(0);
    const [financials, setFinancials] = useState<any>(null); // eslint-disable-next-line @typescript-eslint/no-explicit-any

    // New states for notification
    const [isNotifying, setIsNotifying] = useState(false);
    const [statusMessage, setStatusMessage] = useState("");
    const [statusType, setStatusType] = useState<"success" | "error" | "empty" | "">("");

    const fetchData = async () => {
        try {
            const [metricsRes, trendsRes, distRes] = await Promise.all([
                fetch('http://localhost:8000/api/data/metrics'),
                fetch('http://localhost:8000/api/data/trends'),
                fetch('http://localhost:8000/api/data/distribution')
            ]);

            const metricsData = await metricsRes.json();
            const trendsData = await trendsRes.json();
            const distData = await distRes.json();

            setMetrics(metricsData);
            setTrends(trendsData);
            setDistribution(distData);

            try {
                const finRes = await fetch('http://localhost:8000/api/data/financials');
                const finData = await finRes.json();
                setFinancials(finData);
            } catch (e) {
                console.error("Financials fetch failed", e);
            }

            const totalPeople = distData.reduce((acc: number, curr: any) => {
                const size = parseInt(curr.party_size.split(' ')[0]);
                return acc + (size * curr.value);
            }, 0);
            setRevenue(totalPeople * 35000); // 35k CLP approx

        } catch (error) {
            console.error("Failed to fetch data", error);
        }
    };

    const handleNotifyNext = async () => {
        setIsNotifying(true);
        setStatusMessage("");
        setStatusType("");

        try {
            const response = await fetch("http://127.0.0.1:8000/api/booking/notify-next-waitlist", {
                method: "POST",
            });

            const data = await response.json();

            if (response.ok) {
                if (data.status === "empty") {
                    setStatusMessage(data.message);
                    setStatusType("empty");
                } else {
                    setStatusMessage(`¡Éxito! Notificación enviada a ${data.customer}.`);
                    setStatusType("success");
                }
            } else {
                setStatusMessage(data.detail || "Error al procesar la notificación.");
                setStatusType("error");
            }
        } catch (error) {
            console.error("Error de red:", error);
            setStatusMessage("Error de conexión con el servidor.");
            setStatusType("error");
        } finally {
            setIsNotifying(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    return (
        <div className="min-h-screen bg-[#fdfaf6] text-[#2d1b1b] p-8 font-sans">
            <header className="flex justify-between items-center mb-12 border-b border-[#5c1414]/10 pb-6">
                <div>
                    <h1 className="text-4xl font-serif text-[#5c1414]">Sabor Divino</h1>
                    <p className="text-xs uppercase tracking-[0.3em] text-[#c5a059] mt-1 font-medium">Business Intelligence Dashboard</p>
                </div>
                <Link href="/" className="text-[10px] uppercase tracking-widest text-[#2d1b1b]/40 hover:text-[#5c1414] transition-colors">Volver al Inicio</Link>
            </header>

            {/* Stats Grid + Waitlist Notification */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
                <div className="bg-white p-6 border-l-4 border-[#5c1414] shadow-sm">
                    <h2 className="text-[#2d1b1b]/40 text-[10px] uppercase tracking-widest mb-4 font-bold">Total Reservas</h2>
                    <div className="text-4xl font-serif text-[#5c1414]">
                        {metrics ? metrics.total_bookings ?? 'N/A' : '...'}
                    </div>
                    <div className="mt-4 text-[10px] text-[#c5a059] flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#c5a059] animate-pulse"></span>
                        BigQuery Sync
                    </div>
                </div>

                <div className="bg-white p-6 border-l-4 border-[#c5a059] shadow-sm">
                    <h2 className="text-[#2d1b1b]/40 text-[10px] uppercase tracking-widest mb-4 font-bold">Ingresos Est.</h2>
                    <div className="text-4xl font-serif text-[#2d1b1b]">
                        ${(revenue / 1000000).toFixed(1)}M
                    </div>
                    <div className="mt-4 text-[10px] text-[#2d1b1b]/30 italic">Basado en $35k avg spend</div>
                </div>

                <div className="bg-white p-6 border-l-4 border-[#2d1b1b] shadow-sm">
                    <h2 className="text-[#2d1b1b]/40 text-[10px] uppercase tracking-widest mb-4 font-bold">Beneficio Neto</h2>
                    <div className="text-4xl font-serif text-[#5c1414]">
                        ${financials ? (financials.net_profit / 1000000).toFixed(1) : '...'}M
                    </div>
                    <div className="mt-4 text-[10px] text-[#c5a059]">Revenue - CRM Costs</div>
                </div>

                {/* New Waitlist Action Card */}
                <div className="bg-white p-6 border-l-4 border-[#5c1414] shadow-sm flex flex-col justify-between">
                    <div>
                        <h2 className="text-[#2d1b1b]/40 text-[10px] uppercase tracking-widest mb-2 font-bold flex items-center gap-2">
                            <BellIcon className="w-3 h-3 text-[#5c1414]" />
                            Lista de Espera
                        </h2>
                        <p className="text-[11px] text-[#2d1b1b]/60 leading-tight mb-4">Notifica al siguiente cliente por WhatsApp.</p>
                    </div>

                    <button
                        onClick={handleNotifyNext}
                        disabled={isNotifying}
                        className={`w-full py-2 px-4 rounded text-[10px] uppercase tracking-widest font-bold transition-all ${isNotifying
                                ? "bg-gray-200 text-gray-500 cursor-not-allowed"
                                : "bg-[#5c1414] text-white hover:bg-[#2d1b1b] shadow-md hover:shadow-lg active:scale-95"
                            }`}
                    >
                        {isNotifying ? "Procesando..." : "Notificar Siguiente"}
                    </button>
                </div>
            </div>

            {/* Notification Feedback (Visible if active) */}
            {statusMessage && (
                <div className={`mb-12 p-4 border animate-in fade-in slide-in-from-top-2 duration-500 ${statusType === "success"
                        ? "bg-green-50 border-green-100 text-green-800"
                        : statusType === "empty"
                            ? "bg-amber-50 border-amber-100 text-amber-800"
                            : "bg-red-50 border-red-100 text-red-800"
                    }`}>
                    <div className="max-w-7xl mx-auto flex items-center gap-3">
                        {statusType === "success" ? <CheckCircleIcon className="w-5 h-5 flex-shrink-0" /> : <ExclamationCircleIcon className="w-5 h-5 flex-shrink-0" />}
                        <span className="text-sm font-medium">{statusMessage}</span>
                    </div>
                </div>
            )}

            {/* Charts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Revenue by Source */}
                <div className="bg-white p-8 border border-[#5c1414]/5 shadow-sm lg:col-span-2">
                    <h3 className="text-xl font-serif mb-8 text-[#5c1414]">Rendimiento por Canal (CRM)</h3>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={financials?.sources || []}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                                <XAxis dataKey="source" stroke="#2d1b1b" fontSize={10} axisLine={false} tickLine={false} />
                                <YAxis stroke="#2d1b1b" fontSize={10} axisLine={false} tickLine={false} />
                                <RechartsTooltip
                                    contentStyle={{ backgroundColor: '#fdfaf6', border: '1px solid #5c1414', borderRadius: '4px' }}
                                />
                                <Legend />
                                <Bar dataKey="revenue" fill="#5c1414" name="Ingresos" radius={[4, 4, 0, 0]} />
                                <Bar dataKey="profit" fill="#c5a059" name="Beneficio" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Distribution */}
                <div className="bg-white p-8 border border-[#5c1414]/5 shadow-sm">
                    <h3 className="text-xl font-serif mb-8 text-[#5c1414]">Mesa Promedio</h3>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={distribution}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={70}
                                    outerRadius={90}
                                    paddingAngle={5}
                                    dataKey="value"
                                >
                                    {distribution.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} stroke="none" />
                                    ))}
                                </Pie>
                                <RechartsTooltip contentStyle={{ fontSize: '10px' }} />
                                <Legend iconType="circle" />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Reservation Trends */}
                <div className="bg-[#2d1b1b] p-8 shadow-2xl lg:col-span-3 text-[#fdfaf6]">
                    <div className="flex justify-between items-center mb-8">
                        <h3 className="text-xl font-serif">Tendencias de Reserva (30 días)</h3>
                        <button onClick={fetchData} className="text-[10px] uppercase tracking-widest border border-[#fdfaf6]/20 px-3 py-1 hover:bg-[#fdfaf6] hover:text-[#2d1b1b] transition-all">Sincronizar</button>
                    </div>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={trends}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#fdfaf6/10" vertical={false} opacity={0.1} />
                                <XAxis dataKey="date" stroke="#fdfaf6" fontSize={10} axisLine={false} tickLine={false} opacity={0.5} />
                                <YAxis stroke="#fdfaf6" fontSize={10} axisLine={false} tickLine={false} opacity={0.5} />
                                <RechartsTooltip
                                    contentStyle={{ backgroundColor: '#2d1b1b', border: '1px solid #c5a059', color: '#fdfaf6' }}
                                />
                                <Line type="monotone" dataKey="count" stroke="#c5a059" strokeWidth={2} dot={{ fill: '#c5a059', r: 4 }} activeDot={{ r: 6, stroke: '#fdfaf6', strokeWidth: 2 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            <footer className="mt-12 text-center text-[10px] text-[#2d1b1b]/20 tracking-[0.5em] uppercase border-t border-[#5c1414]/5 pt-8">
                Sabor Divino Analytics Engine v2.0 | Confidential
            </footer>
        </div>
    );
}
