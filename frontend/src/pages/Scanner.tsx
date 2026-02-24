import { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { listWarehouses } from '../api/warehouses';
import { scanLookup, scanReceive, scanPick, scanAdjust } from '../api/scanner';
import type { ScanLookupResult } from '../api/scanner';
import { Html5QrcodeScanner } from 'html5-qrcode';

type ScanMode = 'RECEIVE' | 'PICK' | 'ADJUST';

const REASON_CODES = ['DAMAGE', 'THEFT', 'FOUND', 'DATA_ERROR', 'OTHER'];

export function Scanner() {
    const navigate = useNavigate();
    const inputRef = useRef<HTMLInputElement>(null);
    const [mode, setMode] = useState<ScanMode>('RECEIVE');
    const [warehouseId, setWarehouseId] = useState('');
    const [barcode, setBarcode] = useState('');
    const [quantity, setQuantity] = useState('1');
    const [reasonCode, setReasonCode] = useState('DAMAGE');
    const [expiryDate, setExpiryDate] = useState('');
    const [lookupResult, setLookupResult] = useState<ScanLookupResult | null>(null);
    const [flash, setFlash] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
    const [isProcessing, setIsProcessing] = useState(false);
    const [cameraMode, setCameraMode] = useState(false);

    useEffect(() => {
        if (cameraMode) {
            const scanner = new Html5QrcodeScanner('qr-reader', { fps: 10, qrbox: 250 }, false);
            scanner.render(
                (decodedText) => {
                    setBarcode(decodedText);
                    setCameraMode(false);
                    scanner.clear();
                },
                (error) => {
                    // ignore errors during scanning like "no barcode found"
                }
            );
            return () => {
                scanner.clear().catch(console.error);
            };
        }
    }, [cameraMode]);

    const { data: warehouses } = useQuery({
        queryKey: ['warehouses'],
        queryFn: () => listWarehouses().then(r => r.data.data || []),
    });

    // Auto-focus scan input
    useEffect(() => {
        if (!flash) inputRef.current?.focus();
    }, [flash, lookupResult, mode]);

    // Clear flash after short delay
    useEffect(() => {
        if (flash) {
            const t = setTimeout(() => {
                setFlash(null);
                setLookupResult(null);
                setBarcode('');
                setQuantity('1');
                setExpiryDate('');
                inputRef.current?.focus();
            }, 1200);
            return () => clearTimeout(t);
        }
    }, [flash]);

    const handleScan = useCallback(async () => {
        if (!barcode.trim() || !warehouseId) return;
        setIsProcessing(true);
        try {
            const res = await scanLookup(barcode.trim(), warehouseId);
            setLookupResult(res.data || res as any);
        } catch (err: any) {
            const detail = err.response?.data?.detail;
            const msg = Array.isArray(detail) ? detail.map(e => e.msg).join(', ') : (detail || 'SKU not found');
            setFlash({ message: msg, type: 'error' });
        } finally {
            setIsProcessing(false);
        }
    }, [barcode, warehouseId]);

    const handleConfirm = useCallback(async () => {
        if (!lookupResult || !warehouseId) return;
        setIsProcessing(true);
        try {
            let result: any;
            const qty = parseFloat(quantity);
            if (mode === 'RECEIVE') {
                result = await scanReceive(barcode.trim(), warehouseId, qty, undefined, expiryDate || undefined);
            } else if (mode === 'PICK') {
                result = await scanPick(barcode.trim(), warehouseId, qty);
            } else {
                result = await scanAdjust(barcode.trim(), warehouseId, qty, reasonCode);
            }
            const msg = result?.data?.message || result?.message || `${mode} confirmed`;
            setFlash({ message: msg, type: 'success' });
        } catch (err: any) {
            const detail = err.response?.data?.detail;
            const msg = Array.isArray(detail) ? detail.map(e => e.msg).join(', ') : (detail || 'Operation failed');
            setFlash({ message: msg, type: 'error' });
        } finally {
            setIsProcessing(false);
        }
    }, [lookupResult, warehouseId, mode, barcode, quantity, reasonCode]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            if (!lookupResult) handleScan();
            else handleConfirm();
        }
    };

    // No warehouse selected
    if (!warehouseId) {
        return (
            <div className="scanner-layout">
                <div className="scanner-header">
                    <span className="logo">NEXUS IMS</span>
                    <button className="btn-ghost" style={{ color: 'rgba(255,255,255,0.6)' }} onClick={() => navigate('/')}>✕ Exit</button>
                </div>
                <div className="scanner-body">
                    <div style={{ textAlign: 'center', maxWidth: 320 }}>
                        <h2 style={{ color: '#fff', marginBottom: '0.75rem' }}>Select Warehouse</h2>
                        <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.875rem', marginBottom: '1rem' }}>Choose your active warehouse before scanning</p>
                        {(warehouses || []).map((w: any) => (
                            <button key={w.id} onClick={() => setWarehouseId(w.id)}
                                style={{ width: '100%', marginBottom: '0.5rem', padding: '0.75rem', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)', color: '#fff', fontSize: '0.875rem', justifyContent: 'center' }}>
                                {w.code} — {w.name}
                            </button>
                        ))}
                        {(warehouses || []).length === 0 && <p style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.8125rem' }}>No warehouses found</p>}
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="scanner-layout">
            {/* Flash overlay */}
            {flash && (
                <div className="scan-success" style={{ background: flash.type === 'success' ? 'rgba(5, 150, 105, 0.95)' : 'rgba(220, 38, 38, 0.95)' }}>
                    <div style={{ textAlign: 'center' }}>
                        <div className="checkmark">{flash.type === 'success' ? '✓' : '✕'}</div>
                        <div className="message">{flash.message}</div>
                    </div>
                </div>
            )}

            {/* Header */}
            <div className="scanner-header">
                <span className="logo">NEXUS IMS</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)' }}>
                        {(warehouses || []).find((w: any) => w.id === warehouseId)?.code || 'WH'}
                    </span>
                    <button className="btn-ghost" style={{ color: 'rgba(255,255,255,0.6)' }} onClick={() => navigate('/')}>✕ Exit</button>
                </div>
            </div>

            {/* Body */}
            <div className="scanner-body">
                {/* Mode tabs */}
                <div className="scanner-mode-tabs">
                    {(['RECEIVE', 'PICK', 'ADJUST'] as ScanMode[]).map(m => (
                        <button key={m} className={`scanner-mode-tab ${mode === m ? 'active' : ''}`}
                            onClick={() => { setMode(m); setLookupResult(null); setBarcode(''); }}>
                            {m}
                        </button>
                    ))}
                </div>

                {/* Scan input */}
                <div className="scanner-input-area" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <input ref={inputRef} className="scanner-input" placeholder="Scan barcode or enter SKU code"
                            value={barcode} onChange={e => { setBarcode(e.target.value); if (lookupResult) setLookupResult(null); }}
                            onKeyDown={handleKeyDown} disabled={isProcessing || cameraMode} autoFocus style={{ flex: 1 }} />
                        <button type="button" onClick={() => setCameraMode(!cameraMode)}
                            style={{ padding: '0 1rem', borderRadius: '8px', background: cameraMode ? '#ef4444' : '#3b82f6', color: '#fff' }}>
                            {cameraMode ? 'Close Camera' : '📷 Scan'}
                        </button>
                    </div>
                    <div id="qr-reader" style={{ display: cameraMode ? 'block' : 'none', width: '100%', maxWidth: '400px', margin: '0 auto', background: '#fff', borderRadius: '8px', overflow: 'hidden' }}></div>
                </div>

                {/* Lookup result */}
                {lookupResult && (
                    <div className="scanner-result">
                        <div className="sku-code">{lookupResult.sku_code}</div>
                        <div className="sku-name">{lookupResult.sku_name}</div>
                        <div className="stock-info">
                            <div>
                                <div className="stock-label">Current Stock</div>
                                <div className="stock-value">{lookupResult.current_stock}</div>
                            </div>
                            {lookupResult.unit_cost != null && (
                                <div style={{ textAlign: 'right' }}>
                                    <div className="stock-label">Unit Cost</div>
                                    <div className="stock-value" style={{ fontSize: '1rem' }}>${lookupResult.unit_cost}</div>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Confirm area */}
                {lookupResult && (
                    <div style={{ width: '100%', maxWidth: 400, marginTop: '1rem' }}>
                        <div className="scanner-confirm">
                            <input type="number" value={quantity} onChange={e => setQuantity(e.target.value)}
                                placeholder="Qty" min="0" step="1" />
                            <button onClick={handleConfirm} disabled={isProcessing}
                                style={{ background: mode === 'PICK' ? '#d97706' : mode === 'ADJUST' ? '#6366f1' : 'var(--color-green)' }}>
                                {isProcessing ? '...' : `Confirm ${mode}`}
                            </button>
                        </div>
                        {mode === 'ADJUST' && (
                            <select value={reasonCode} onChange={e => setReasonCode(e.target.value)}
                                style={{ width: '100%', marginTop: '0.5rem', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)', color: '#fff', padding: '0.5rem', borderRadius: '6px' }}>
                                {REASON_CODES.map(r => <option key={r} value={r}>{r}</option>)}
                            </select>
                        )}
                        {mode === 'RECEIVE' && (
                            <input type="date" value={expiryDate} onChange={e => setExpiryDate(e.target.value)}
                                placeholder="Expiry Date (optional)"
                                style={{ width: '100%', marginTop: '0.5rem', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)', color: '#fff', padding: '0.5rem', borderRadius: '6px' }} />
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
