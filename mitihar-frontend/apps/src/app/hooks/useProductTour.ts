import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { useQuery, useMutation } from '@tanstack/react-query';
import type { EventData, Step } from 'react-joyride';
import { STATUS, EVENTS, ACTIONS } from 'react-joyride';
import { doctorApi } from '../../lib/doctorApi';
import { qk } from '../../lib/queryKeys';

interface TourStep extends Step {
  route: string;
}

// SMOKE TEST: only 2 of the eventual 5 steps. Extended in Task 9 once this
// proves cross-route attach works.
const TOUR_STEPS: TourStep[] = [
  {
    route: '/doctor/overview',
    target: '[data-tour="tour-overview"]',
    title: 'Welcome to Mitihar',
    content: 'This is your dashboard home — a snapshot of your patients, requests, and this week\'s plans.',
    skipBeacon: true,
  },
  {
    route: '/doctor/patients',
    target: '[data-tour="tour-patients"]',
    title: 'Your Patients',
    content: 'Every patient assigned to you shows up here.',
    skipBeacon: true,
  },
];

function waitForElement(selector: string, timeoutMs = 3000): Promise<boolean> {
  return new Promise(resolve => {
    if (document.querySelector(selector)) {
      resolve(true);
      return;
    }
    const observer = new MutationObserver(() => {
      if (document.querySelector(selector)) {
        observer.disconnect();
        resolve(true);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    setTimeout(() => {
      observer.disconnect();
      resolve(!!document.querySelector(selector));
    }, timeoutMs);
  });
}

export function useProductTour() {
  const location = useLocation();
  const navigate = useNavigate();
  const [run, setRun] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const startedRef = useRef(false);

  const { data: dash } = useQuery({
    queryKey: qk.dashboard(),
    queryFn: doctorApi.getDashboard,
  });

  const completeMutation = useMutation({
    mutationFn: doctorApi.completeTour,
  });

  // Start the tour once, only if the doctor has never completed it.
  useEffect(() => {
    if (startedRef.current) return;
    if (dash === undefined) return;
    startedRef.current = true;
    if (dash.product_tour_completed_at === null) {
      setStepIndex(0);
      setRun(true);
    }
  }, [dash]);

  const advanceTo = async (nextIndex: number) => {
    const next = TOUR_STEPS[nextIndex];
    if (!next) {
      setRun(false);
      completeMutation.mutate();
      return;
    }
    if (next.route !== location.pathname) {
      setRun(false);
      navigate(next.route);
      const found = await waitForElement(next.target as string);
      if (!found) {
        // Target never mounted — stop rather than spotlight nothing.
        setRun(false);
        return;
      }
    }
    setStepIndex(nextIndex);
    setRun(true);
  };

  const onEvent = (data: EventData) => {
    const { status, type, index, action } = data;
    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      setRun(false);
      completeMutation.mutate();
      return;
    }
    if (type === EVENTS.STEP_AFTER && action === ACTIONS.NEXT) {
      advanceTo(index + 1);
    }
  };

  return { run, stepIndex, steps: TOUR_STEPS, onEvent };
}
