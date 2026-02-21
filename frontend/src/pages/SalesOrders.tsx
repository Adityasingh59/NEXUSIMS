import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    getSalesOrders,
    createSalesOrder,
    allocateSalesOrder,
    shipSalesOrder,
    cancelSalesOrder,
    type SalesOrder,
    type CreateSalesOrderValues
} from '../api/sales';
import { skusApi, type SKU } from '../api/skus';
import { listWarehouses, type Warehouse } from '../api/warehouses';

export const SalesOrders: React.FC = () => {
    const queryClient = useQueryClient();
    const [activeTab, setActiveTab] = useState<'list' | 'create'>('list');

    // Queries
    const { data: orders = [], isLoading: isLoadingOrders } = useQuery({
        queryKey: ['sales-orders'],
        queryFn: getSalesOrders,
    });

    const { data: skusData } = useQuery({
        queryKey: ['skus'],
        queryFn: () => skusApi.list({ page_size: 100 }), // In a real app, this should be a paginated searchable dropdown
    });
    const skus = (skusData?.data?.data as unknown as SKU[]) || [];

    const { data: warehousesData } = useQuery({
        queryKey: ['warehouses'],
        queryFn: listWarehouses,
    });
    const warehouses = (warehousesData?.data?.data as unknown as Warehouse[]) || [];
    const defaultWarehouse = warehouses.find((w: Warehouse) => w.name === 'Main Warehouse' || w.is_active) || warehouses[0];

    // Forms State
    const [customerName, setCustomerName] = useState('');
    const [orderReference, setOrderReference] = useState('');
    const [shippingAddress, setShippingAddress] = useState('');
    const [lines, setLines] = useState([{ sku_id: '', quantity: 1, unit_price: 0 }]);
    const [errorMsg, setErrorMsg] = useState('');

    // Mutations
    const createOrderMutation = useMutation<SalesOrder, Error, CreateSalesOrderValues>({
        mutationFn: createSalesOrder,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['sales-orders'] });
            setActiveTab('list');
            setCustomerName('');
            setOrderReference('');
            setShippingAddress('');
            setLines([{ sku_id: '', quantity: 1, unit_price: 0 }]);
            setErrorMsg('');
        },
        onError: (error: any) => {
            setErrorMsg(error.response?.data?.detail || 'Failed to create sales order');
        }
    });

    const allocateMutation = useMutation<any, Error, { id: string; warehouseId: string }>({
        mutationFn: ({ id, warehouseId }) => allocateSalesOrder(id, warehouseId),
        onSuccess: (data) => {
            if (data && data.shortages) {
                // If the backend returns shortages inside the 200 response
                setErrorMsg(`Allocation Failed: Shortage of ${data.shortages.length} SKUs.`);
            } else {
                queryClient.invalidateQueries({ queryKey: ['sales-orders'] });
                setErrorMsg('');
            }
        },
        onError: (error: any) => {
            setErrorMsg(error.response?.data?.detail || error.response?.data?.error || 'Failed to allocate order');
        }
    });

    const shipMutation = useMutation<SalesOrder, Error, { id: string; warehouseId: string }>({
        mutationFn: ({ id, warehouseId }) => shipSalesOrder(id, warehouseId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['sales-orders'] });
            setErrorMsg('');
        },
        onError: (error: any) => {
            setErrorMsg(error.response?.data?.detail || 'Failed to ship order');
        }
    });

    const cancelMutation = useMutation<SalesOrder, Error, { id: string; warehouseId: string }>({
        mutationFn: ({ id, warehouseId }) => cancelSalesOrder(id, warehouseId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['sales-orders'] });
            setErrorMsg('');
        },
        onError: (error: any) => {
            setErrorMsg(error.response?.data?.detail || 'Failed to cancel order');
        }
    });

    const handleAddLine = () => {
        setLines([...lines, { sku_id: '', quantity: 1, unit_price: 0 }]);
    };

    const handleLineChange = (index: number, field: string, value: any) => {
        const newLines = [...lines];
        newLines[index] = { ...newLines[index], [field]: value };
        setLines(newLines);
    };

    const handleRemoveLine = (index: number) => {
        const newLines = lines.filter((_, i) => i !== index);
        setLines(newLines);
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!customerName || lines.length === 0 || lines.some(l => !l.sku_id || l.quantity <= 0)) {
            setErrorMsg('Please fill in all required fields correctly.');
            return;
        }

        createOrderMutation.mutate({
            customer_name: customerName,
            order_reference: orderReference || undefined,
            shipping_address: shippingAddress || undefined,
            lines: lines.map(l => ({
                ...l,
                quantity: Number(l.quantity),
                unit_price: Number(l.unit_price)
            }))
        });
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-semibold text-slate-800">Sales Orders</h1>
            </div>

            {errorMsg && (
                <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-md">
                    <p className="text-sm text-red-700 font-medium">{errorMsg}</p>
                </div>
            )}

            {/* Tabs */}
            <div className="border-b border-slate-200">
                <nav className="-mb-px flex space-x-8">
                    <button
                        onClick={() => setActiveTab('list')}
                        className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${activeTab === 'list'
                            ? 'border-blue-500 text-blue-600'
                            : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                            }`}
                    >
                        All Orders
                    </button>
                    <button
                        onClick={() => setActiveTab('create')}
                        className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${activeTab === 'create'
                            ? 'border-blue-500 text-blue-600'
                            : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                            }`}
                    >
                        Create Order
                    </button>
                </nav>
            </div>

            {/* List View */}
            {activeTab === 'list' && (
                <div className="bg-white shadow rounded-lg overflow-hidden border border-slate-200">
                    <table className="min-w-full divide-y divide-slate-200">
                        <thead className="bg-slate-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Date</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Customer</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Ref</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-slate-200">
                            {isLoadingOrders ? (
                                <tr><td colSpan={5} className="px-6 py-4 text-center text-slate-500">Loading...</td></tr>
                            ) : orders.length === 0 ? (
                                <tr><td colSpan={5} className="px-6 py-4 text-center text-slate-500">No sales orders found.</td></tr>
                            ) : (
                                orders.map((order) => (
                                    <tr key={order.id} className="hover:bg-slate-50">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                                            {new Date(order.created_at).toLocaleDateString()}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">
                                            {order.customer_name}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                                            {order.order_reference || '-'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${order.status === 'SHIPPED' ? 'bg-green-100 text-green-800' :
                                                order.status === 'PROCESSING' ? 'bg-blue-100 text-blue-800' :
                                                    order.status === 'CANCELLED' ? 'bg-red-100 text-red-800' :
                                                        'bg-yellow-100 text-yellow-800'
                                                }`}>
                                                {order.status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                                            {order.status === 'PENDING' && (
                                                <button
                                                    onClick={() => defaultWarehouse && allocateMutation.mutate({ id: order.id, warehouseId: defaultWarehouse.id })}
                                                    disabled={allocateMutation.isPending}
                                                    className="text-blue-600 hover:text-blue-900 bg-blue-50 px-3 py-1 rounded border border-blue-200"
                                                >
                                                    Allocate Stock
                                                </button>
                                            )}
                                            {order.status === 'PROCESSING' && (
                                                <button
                                                    onClick={() => defaultWarehouse && shipMutation.mutate({ id: order.id, warehouseId: defaultWarehouse.id })}
                                                    disabled={shipMutation.isPending}
                                                    className="text-green-600 hover:text-green-900 bg-green-50 px-3 py-1 rounded border border-green-200"
                                                >
                                                    Ship Order
                                                </button>
                                            )}
                                            {(order.status === 'PENDING' || order.status === 'PROCESSING') && (
                                                <button
                                                    onClick={() => defaultWarehouse && cancelMutation.mutate({ id: order.id, warehouseId: defaultWarehouse.id })}
                                                    className="text-red-600 hover:text-red-900 px-3 py-1 rounded"
                                                >
                                                    Cancel
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Create View */}
            {activeTab === 'create' && (
                <form onSubmit={handleSubmit} className="bg-white shadow rounded-lg p-6 border border-slate-200">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Customer Name *</label>
                            <input
                                type="text"
                                required
                                value={customerName}
                                onChange={(e) => setCustomerName(e.target.value)}
                                className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                                placeholder="Acme Corp"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Order Reference</label>
                            <input
                                type="text"
                                value={orderReference}
                                onChange={(e) => setOrderReference(e.target.value)}
                                className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                                placeholder="PO-2023-XYZ"
                            />
                        </div>
                        <div className="md:col-span-2">
                            <label className="block text-sm font-medium text-slate-700 mb-1">Shipping Address</label>
                            <textarea
                                value={shippingAddress}
                                onChange={(e) => setShippingAddress(e.target.value)}
                                rows={2}
                                className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                                placeholder="123 Delivery St..."
                            />
                        </div>
                    </div>

                    <div className="mb-4 flex items-center justify-between">
                        <h3 className="text-lg font-medium text-slate-900">Order Lines</h3>
                        <button
                            type="button"
                            onClick={handleAddLine}
                            className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
                        >
                            + Add Item
                        </button>
                    </div>

                    <div className="space-y-4">
                        {lines.map((line, index) => (
                            <div key={index} className="flex flex-wrap md:flex-nowrap items-end gap-4 p-4 border border-slate-200 rounded-md bg-slate-50">
                                <div className="w-full md:w-2/5">
                                    <label className="block text-xs font-medium text-slate-700 mb-1">SKU *</label>
                                    <select
                                        required
                                        value={line.sku_id}
                                        onChange={(e) => handleLineChange(index, 'sku_id', e.target.value)}
                                        className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm bg-white"
                                    >
                                        <option value="">Select SKU...</option>
                                        {skus.map((sku: SKU) => (
                                            <option key={sku.id} value={sku.id}>{sku.sku_code} - {sku.name}</option>
                                        ))}
                                    </select>
                                </div>

                                <div className="w-full md:w-1/5">
                                    <label className="block text-xs font-medium text-slate-700 mb-1">Quantity *</label>
                                    <input
                                        type="number"
                                        min="1"
                                        step="1"
                                        required
                                        value={line.quantity}
                                        onChange={(e) => handleLineChange(index, 'quantity', e.target.value)}
                                        className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                                    />
                                </div>

                                <div className="w-full md:w-1/5">
                                    <label className="block text-xs font-medium text-slate-700 mb-1">Unit Price ($)</label>
                                    <input
                                        type="number"
                                        min="0"
                                        step="0.01"
                                        value={line.unit_price}
                                        onChange={(e) => handleLineChange(index, 'unit_price', e.target.value)}
                                        className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                                    />
                                </div>

                                <div className="w-full md:w-auto mt-2 md:mt-0">
                                    <button
                                        type="button"
                                        onClick={() => handleRemoveLine(index)}
                                        className="text-red-500 hover:text-red-700 bg-red-50 p-2 rounded border border-red-200"
                                        disabled={lines.length === 1}
                                    >
                                        Remove
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="mt-8 pt-5 border-t border-slate-200 flex justify-end">
                        <button
                            type="button"
                            onClick={() => setActiveTab('list')}
                            className="bg-white py-2 px-4 border border-slate-300 rounded-md shadow-sm text-sm font-medium text-slate-700 hover:bg-slate-50 mr-3"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={createOrderMutation.isPending}
                            className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                        >
                            {createOrderMutation.isPending ? 'Saving...' : 'Create Sales Order'}
                        </button>
                    </div>
                </form>
            )}
        </div>
    );
};
