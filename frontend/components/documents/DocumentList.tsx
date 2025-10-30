'use client';

import { useState } from 'react';
import { format } from 'date-fns';
import {
  FileText,
  Download,
  Trash2,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Star,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Alert } from '@/components/ui/alert';
import { CustomerDocument, CustomerDocumentVerificationStatus } from '@/types';
import { documentsAPI } from '@/lib/api/documents';

interface DocumentListProps {
  documents: CustomerDocument[];
  onUpdate?: () => void;
  canManage?: boolean;
}

export function DocumentList({ documents, onUpdate, canManage = false }: DocumentListProps) {
  const [selectedDoc, setSelectedDoc] = useState<CustomerDocument | null>(null);
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getStatusIcon = (status: CustomerDocumentVerificationStatus) => {
    switch (status) {
      case 'verified':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'rejected':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'expired':
        return <AlertTriangle className="h-5 w-5 text-orange-500" />;
      default:
        return <Clock className="h-5 w-5 text-yellow-500" />;
    }
  };

  const getStatusBadge = (status: CustomerDocumentVerificationStatus) => {
    const colors = {
      pending: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      verified: 'bg-green-100 text-green-800 border-green-200',
      rejected: 'bg-red-100 text-red-800 border-red-200',
      expired: 'bg-orange-100 text-orange-800 border-orange-200',
    };

    return colors[status] || colors.pending;
  };

  const handleVerify = async (doc: CustomerDocument) => {
    if (!canManage) return;

    setIsProcessing(true);
    setError(null);

    try {
      await documentsAPI.verifyDocument(doc.id);
      onUpdate?.();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to verify document');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = async () => {
    if (!selectedDoc || !canManage || !rejectionReason.trim()) {
      setError('Please provide a rejection reason');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      await documentsAPI.rejectDocument(selectedDoc.id, rejectionReason);
      setShowRejectDialog(false);
      setRejectionReason('');
      setSelectedDoc(null);
      onUpdate?.();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to reject document');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleMarkPrimary = async (doc: CustomerDocument) => {
    setIsProcessing(true);
    setError(null);

    try {
      await documentsAPI.markAsPrimary(doc.id);
      onUpdate?.();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to mark document as primary');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedDoc) return;

    setIsProcessing(true);
    setError(null);

    try {
      await documentsAPI.deleteDocument(selectedDoc.id);
      setShowDeleteDialog(false);
      setSelectedDoc(null);
      onUpdate?.();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to delete document');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = (doc: CustomerDocument) => {
    // Open document in new tab for download
    window.open(doc.document_file, '_blank');
  };

  if (documents.length === 0) {
    return (
      <Card className="p-8">
        <div className="text-center text-muted-foreground">
          <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
          <p>No documents uploaded yet</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <span className="ml-2">{error}</span>
        </Alert>
      )}

      {documents.map((doc) => (
        <Card key={doc.id} className="p-4">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center space-x-3 mb-2">
                <FileText className="h-6 w-6 text-primary" />
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <h4 className="font-semibold">{doc.title}</h4>
                    {doc.is_primary && (
                      <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" />
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {doc.document_type_display}
                  </p>
                </div>
              </div>

              {doc.description && (
                <p className="text-sm text-muted-foreground mb-2">{doc.description}</p>
              )}

              <div className="flex items-center space-x-4 text-xs text-muted-foreground mb-3">
                <span>Size: {doc.file_size_mb} MB</span>
                <span>Type: {doc.file_type}</span>
                <span>Uploaded: {format(new Date(doc.created_at), 'MMM dd, yyyy')}</span>
                {doc.expiry_date && (
                  <span
                    className={doc.is_expired ? 'text-red-500 font-medium' : ''}
                  >
                    {doc.is_expired ? 'Expired' : 'Expires'}:{' '}
                    {format(new Date(doc.expiry_date), 'MMM dd, yyyy')}
                  </span>
                )}
              </div>

              <div className="flex items-center space-x-2">
                <span
                  className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusBadge(
                    doc.verification_status
                  )}`}
                >
                  {getStatusIcon(doc.verification_status)}
                  <span className="ml-1">{doc.verification_status_display}</span>
                </span>
              </div>

              {doc.rejection_reason && (
                <Alert variant="destructive" className="mt-3">
                  <p className="text-sm">
                    <strong>Rejection Reason:</strong> {doc.rejection_reason}
                  </p>
                </Alert>
              )}

              {doc.verified_by_name && doc.verified_at && (
                <p className="text-xs text-muted-foreground mt-2">
                  {doc.verification_status === 'verified' ? 'Verified' : 'Rejected'} by{' '}
                  {doc.verified_by_name} on{' '}
                  {format(new Date(doc.verified_at), 'MMM dd, yyyy HH:mm')}
                </p>
              )}
            </div>

            <div className="flex flex-col space-y-2 ml-4">
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleDownload(doc)}
              >
                <Download className="h-4 w-4 mr-1" />
                Download
              </Button>

              {canManage && doc.verification_status === 'pending' && (
                <>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleVerify(doc)}
                    disabled={isProcessing}
                    className="text-green-600 border-green-200 hover:bg-green-50"
                  >
                    <CheckCircle className="h-4 w-4 mr-1" />
                    Verify
                  </Button>

                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedDoc(doc);
                      setShowRejectDialog(true);
                    }}
                    disabled={isProcessing}
                    className="text-red-600 border-red-200 hover:bg-red-50"
                  >
                    <XCircle className="h-4 w-4 mr-1" />
                    Reject
                  </Button>
                </>
              )}

              {!doc.is_primary && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleMarkPrimary(doc)}
                  disabled={isProcessing}
                >
                  <Star className="h-4 w-4 mr-1" />
                  Mark Primary
                </Button>
              )}

              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setSelectedDoc(doc);
                  setShowDeleteDialog(true);
                }}
                disabled={isProcessing}
                className="text-red-600 border-red-200 hover:bg-red-50"
              >
                <Trash2 className="h-4 w-4 mr-1" />
                Delete
              </Button>
            </div>
          </div>
        </Card>
      ))}

      {/* Reject Dialog */}
      <Dialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject Document</DialogTitle>
            <DialogDescription>
              Please provide a reason for rejecting this document. This will be visible
              to the customer.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="rejection_reason">Rejection Reason *</Label>
              <Textarea
                id="rejection_reason"
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="Explain why this document is being rejected..."
                rows={4}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowRejectDialog(false);
                setRejectionReason('');
                setSelectedDoc(null);
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleReject}
              disabled={isProcessing || !rejectionReason.trim()}
            >
              {isProcessing ? 'Rejecting...' : 'Reject Document'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Document</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this document? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowDeleteDialog(false);
                setSelectedDoc(null);
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={isProcessing}
            >
              {isProcessing ? 'Deleting...' : 'Delete Document'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
