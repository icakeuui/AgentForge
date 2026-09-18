import { toast } from 'sonner'

export const notify = {
  success: (message: string) => toast.success(message),
  info: (message: string) => toast.info(message),
  warning: (message: string) => toast.warning(message),
  error: (message: string) => toast.error(message),
}
