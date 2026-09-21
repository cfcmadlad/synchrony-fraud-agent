import { motion, AnimatePresence, MotionConfig } from "motion/react";
import { Pin } from "lucide-react";
import { FaCreditCard, FaReceipt, FaSackDollar, FaWallet } from "react-icons/fa6";
import { StatusBadge } from "./common";

const EVENT_ICONS = {
  loan_disbursement: FaSackDollar,
  installment_repayment: FaCreditCard,
  fee_charge: FaReceipt,
  account_funding: FaWallet,
};

const springConfig = { type: "spring", stiffness: 400, damping: 40 };

export default function PinnedTransactions({ transactions, onUnpin, onOpen }) {
  if (transactions.length === 0) return null;

  return (
    <MotionConfig transition={springConfig}>
      <motion.div layout initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-5">
        <motion.h3 layout className="mb-2 ml-0.5 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-dim)]">
          Pinned for follow-up
        </motion.h3>
        <div className="flex flex-col gap-2">
          <AnimatePresence mode="popLayout" initial={false}>
            {transactions.map((tx) => {
              const Icon = EVENT_ICONS[tx.event_type] || FaWallet;
              return (
                <motion.div
                  key={tx.id}
                  layoutId={`pinned-${tx.id}`}
                  layout
                  initial={{ opacity: 0, scale: 0.96 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.96 }}
                  className="group flex items-center justify-between gap-3 rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] p-3 shadow-sm transition-shadow hover:shadow-md"
                >
                  <div
                    className="flex min-w-0 flex-1 cursor-pointer items-center gap-3"
                    onClick={() => onOpen(tx.id)}
                  >
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--bg-elevated-2)] text-[var(--accent)]">
                      <Icon size={16} />
                    </div>
                    <div className="min-w-0">
                      <h4 className="truncate text-[13.5px] font-semibold text-[var(--text-h)]">
                        {tx.origin_account}
                      </h4>
                      <p className="truncate text-[12px] text-[var(--text-dim)]">
                        {tx.event_type.replace("_", " ")} · ${tx.amount.toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    <StatusBadge status={tx.status} />
                    <motion.button
                      layout
                      onClick={() => onUnpin(tx.id)}
                      className="flex h-7 w-7 items-center justify-center rounded-full bg-amber-400 text-white transition-transform hover:scale-105"
                      title="Unpin"
                      type="button"
                    >
                      <Pin size={13} className="fill-white" />
                    </motion.button>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      </motion.div>
    </MotionConfig>
  );
}
