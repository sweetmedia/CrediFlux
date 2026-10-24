import { beforeEach, describe, expect, it, vi } from 'vitest';

const post = vi.fn();
vi.mock('@/lib/api/client', () => ({ apiClient: { post: (...args: unknown[]) => post(...args) } }));

import { authAPI } from '@/lib/api/auth';

describe('authAPI.regenerateBackupCodes', () => {
  beforeEach(() => post.mockReset());

  it('envía la contraseña y el código TOTP actual', async () => {
    post.mockResolvedValue({ message: 'ok', backup_codes: ['A'] });
    await authAPI.regenerateBackupCodes('clave-123', '123456');
    expect(post).toHaveBeenCalledWith('/api/users/auth/2fa/backup-codes/', {
      password: 'clave-123',
      code: '123456',
    });
  });
});
