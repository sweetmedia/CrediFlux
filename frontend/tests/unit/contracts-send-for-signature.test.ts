import { beforeEach, describe, expect, it, vi } from 'vitest';

const post = vi.fn();
vi.mock('@/lib/api/client', () => ({ apiClient: { post: (...args: unknown[]) => post(...args) } }));

import { canSendForSignature, contractsAPI, isValidSignatureDays } from '@/lib/api/contracts';

describe('canSendForSignature', () => {
  it.each([
    ['draft', false, true],
    ['pending_signature', false, true],
    ['draft', true, false],
    ['pending_signature', true, false],
    ['signed', false, false],
    ['active', false, false],
    ['completed', false, false],
    ['cancelled', false, false],
  ] as const)('status %s archivado=%s → %s', (status, is_archived, expected) => {
    expect(canSendForSignature({ status, is_archived })).toBe(expected);
  });
});

describe('isValidSignatureDays', () => {
  it.each([[1, true], [7, true], [30, true], [0, false], [-1, false], [31, false], [7.5, false], [NaN, false]])(
    '%s → %s',
    (days, expected) => {
      expect(isValidSignatureDays(days)).toBe(expected);
    }
  );
});

describe('contractsAPI.sendForSignature', () => {
  beforeEach(() => post.mockReset());

  it('envía 7 días por defecto', async () => {
    post.mockResolvedValue({ message: 'ok', token_id: 't', expires_at: 'x' });
    await contractsAPI.sendForSignature('c1', 'cliente@crediflux.test');
    expect(post).toHaveBeenCalledWith('/api/loans/contracts/c1/send_for_signature/', {
      email: 'cliente@crediflux.test',
      days_valid: 7,
    });
  });

  it.each([0, -1, 31, 7.5])('rechaza %s días sin llamar al backend', async (days) => {
    await expect(contractsAPI.sendForSignature('c1', 'cliente@crediflux.test', days)).rejects.toThrow(
      'entre 1 y 30'
    );
    expect(post).not.toHaveBeenCalled();
  });
});
