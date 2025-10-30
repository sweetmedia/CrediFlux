'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Upload, X, FileText, CheckCircle, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
import { Alert } from '@/components/ui/alert';
import { documentsAPI } from '@/lib/api/documents';
import { CustomerDocumentType } from '@/types';

const documentTypes: { value: CustomerDocumentType; label: string }[] = [
  { value: 'id_card', label: 'ID Card / Cédula' },
  { value: 'passport', label: 'Passport' },
  { value: 'drivers_license', label: 'Driver\'s License' },
  { value: 'proof_of_income', label: 'Proof of Income' },
  { value: 'bank_statement', label: 'Bank Statement' },
  { value: 'proof_of_address', label: 'Proof of Address' },
  { value: 'employment_letter', label: 'Employment Letter' },
  { value: 'tax_return', label: 'Tax Return' },
  { value: 'business_license', label: 'Business License' },
  { value: 'utility_bill', label: 'Utility Bill' },
  { value: 'contract', label: 'Contract / Agreement' },
  { value: 'other', label: 'Other Document' },
];

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_FILE_TYPES = [
  'application/pdf',
  'image/jpeg',
  'image/jpg',
  'image/png',
  'image/gif',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
];

const documentSchema = z.object({
  document_type: z.string().min(1, 'Document type is required'),
  title: z.string().min(1, 'Title is required').max(200, 'Title must be less than 200 characters'),
  description: z.string().optional(),
  issue_date: z.string().optional(),
  expiry_date: z.string().optional(),
  notes: z.string().optional(),
  is_primary: z.boolean().optional(),
});

type DocumentFormData = z.infer<typeof documentSchema>;

interface DocumentUploadFormProps {
  customerId: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function DocumentUploadForm({
  customerId,
  onSuccess,
  onCancel,
}: DocumentUploadFormProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<DocumentFormData>({
    resolver: zodResolver(documentSchema),
  });

  const validateFile = (file: File): boolean => {
    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      setFileError(`File size exceeds 10MB limit. Current size: ${(file.size / (1024 * 1024)).toFixed(2)}MB`);
      return false;
    }

    // Check file type
    if (!ALLOWED_FILE_TYPES.includes(file.type)) {
      setFileError(`File type '${file.type}' is not allowed. Allowed types: PDF, JPG, PNG, GIF, Word, Excel`);
      return false;
    }

    setFileError(null);
    return true;
  };

  const handleFileSelect = (file: File) => {
    if (validateFile(file)) {
      setSelectedFile(file);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setFileError(null);
  };

  const onSubmit = async (data: DocumentFormData) => {
    if (!selectedFile) {
      setFileError('Please select a file to upload');
      return;
    }

    setIsUploading(true);
    setUploadError(null);

    try {
      await documentsAPI.uploadDocument({
        customer: customerId,
        document_type: data.document_type as CustomerDocumentType,
        title: data.title,
        description: data.description,
        document_file: selectedFile,
        issue_date: data.issue_date,
        expiry_date: data.expiry_date,
        notes: data.notes,
        is_primary: data.is_primary || false,
      });

      setUploadSuccess(true);
      reset();
      setSelectedFile(null);

      // Call onSuccess callback after a short delay
      setTimeout(() => {
        onSuccess?.();
      }, 1500);
    } catch (error: any) {
      console.error('Upload error:', error);
      setUploadError(
        error.response?.data?.detail ||
          error.message ||
          'Failed to upload document. Please try again.'
      );
    } finally {
      setIsUploading(false);
    }
  };

  if (uploadSuccess) {
    return (
      <Card className="p-6">
        <div className="flex flex-col items-center justify-center space-y-4 text-center">
          <CheckCircle className="h-16 w-16 text-green-500" />
          <div>
            <h3 className="text-lg font-semibold">Document Uploaded Successfully!</h3>
            <p className="text-sm text-muted-foreground mt-1">
              The document has been uploaded and is pending verification.
            </p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Document Type */}
        <div className="space-y-2">
          <Label htmlFor="document_type">Document Type *</Label>
          <select
            id="document_type"
            {...register('document_type')}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <option value="">Select document type</option>
            {documentTypes.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
          {errors.document_type && (
            <p className="text-sm text-red-500">{errors.document_type.message}</p>
          )}
        </div>

        {/* Title */}
        <div className="space-y-2">
          <Label htmlFor="title">Document Title *</Label>
          <Input
            id="title"
            {...register('title')}
            placeholder="e.g., National ID Card"
          />
          {errors.title && (
            <p className="text-sm text-red-500">{errors.title.message}</p>
          )}
        </div>

        {/* Description */}
        <div className="space-y-2">
          <Label htmlFor="description">Description (Optional)</Label>
          <Textarea
            id="description"
            {...register('description')}
            placeholder="Add additional information about this document"
            rows={3}
          />
        </div>

        {/* File Upload */}
        <div className="space-y-2">
          <Label>Document File *</Label>

          {!selectedFile ? (
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                isDragging
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
              }`}
            >
              <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-sm text-muted-foreground mb-2">
                Drag and drop your file here, or click to browse
              </p>
              <p className="text-xs text-muted-foreground mb-4">
                Max size: 10MB. Supported: PDF, JPG, PNG, GIF, Word, Excel
              </p>
              <input
                type="file"
                onChange={handleFileInputChange}
                accept=".pdf,.jpg,.jpeg,.png,.gif,.doc,.docx,.xls,.xlsx"
                className="hidden"
                id="file-upload"
              />
              <Button
                type="button"
                variant="outline"
                onClick={() => document.getElementById('file-upload')?.click()}
              >
                Select File
              </Button>
            </div>
          ) : (
            <div className="border rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <FileText className="h-8 w-8 text-primary" />
                  <div>
                    <p className="text-sm font-medium">{selectedFile.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                  </div>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleRemoveFile}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          {fileError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <span className="ml-2 text-sm">{fileError}</span>
            </Alert>
          )}
        </div>

        {/* Dates */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="issue_date">Issue Date (Optional)</Label>
            <Input id="issue_date" type="date" {...register('issue_date')} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="expiry_date">Expiry Date (Optional)</Label>
            <Input id="expiry_date" type="date" {...register('expiry_date')} />
          </div>
        </div>

        {/* Notes */}
        <div className="space-y-2">
          <Label htmlFor="notes">Notes (Optional)</Label>
          <Textarea
            id="notes"
            {...register('notes')}
            placeholder="Add any additional notes"
            rows={2}
          />
        </div>

        {/* Primary Checkbox */}
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="is_primary"
            {...register('is_primary')}
            className="rounded border-input"
          />
          <Label htmlFor="is_primary" className="font-normal cursor-pointer">
            Mark as primary document of this type
          </Label>
        </div>

        {/* Error Alert */}
        {uploadError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <span className="ml-2 text-sm">{uploadError}</span>
          </Alert>
        )}

        {/* Actions */}
        <div className="flex justify-end space-x-3">
          {onCancel && (
            <Button type="button" variant="outline" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button type="submit" disabled={isUploading || !selectedFile}>
            {isUploading ? 'Uploading...' : 'Upload Document'}
          </Button>
        </div>
      </form>
    </Card>
  );
}
