/*
 * Finding 055, defect 2. libical returns its own search budget as an occurrence
 * when BYSETPOS can never be satisfied by any period of the rule.
 *
 * Compiles against libical 3.x and 4.x (the #if picks the parse API).
 *   gcc -O2 -I<prefix>/include -o p 055-libical-setpos-budget.c -L<prefix>/lib -lical
 *   LD_LIBRARY_PATH=<prefix>/lib ./p
 * Expected output for every row here is an empty set, except the BYSETPOS=-1 row.
 * Recorded output for three builds: 055-libical-output.txt.
 */
#include <stdio.h>
#include <libical/ical.h>
static void run(const char *rr, const char *ds, int n){
#if ICAL_MAJOR_VERSION >= 4
  struct icalrecurrencetype *r = icalrecurrencetype_new_from_string(rr);
  if(!r || r->freq==ICAL_NO_RECURRENCE){ printf("%-44s (parse failed)\n", rr); return; }
#else
  struct icalrecurrencetype r = icalrecurrencetype_from_string(rr);
  if(r.freq==ICAL_NO_RECURRENCE){ printf("%-44s (parse failed)\n", rr); return; }
#endif
  struct icaltimetype start = icaltime_from_string(ds);
  icalrecur_iterator *it = icalrecur_iterator_new(r, start);
  printf("%-44s ", rr);
  if(!it){ printf("(no iterator)\n"); return; }
  for(int i=0;i<n;i++){
    struct icaltimetype t = icalrecur_iterator_next(it);
    if(icaltime_is_null_time(t)) { printf("<end>"); break; }
    printf("%s ", icaltime_as_ical_string(t));
  }
  printf("\n"); icalrecur_iterator_free(it);
}
int main(void){
  printf("libical %d.%d\n", ICAL_MAJOR_VERSION, ICAL_MINOR_VERSION);
  run("FREQ=WEEKLY;BYDAY=MO,WE;BYMONTH=6;BYSETPOS=-1","20260601T090000",4);
  run("FREQ=WEEKLY;BYDAY=MO,WE;BYMONTH=6;BYSETPOS=-3","20260601T090000",4);
  run("FREQ=WEEKLY;BYDAY=MO,WE;BYMONTH=6;BYSETPOS=3","20260601T090000",4);
  run("FREQ=WEEKLY;BYDAY=MO,WE;BYSETPOS=5","20260601T090000",4);
  run("FREQ=WEEKLY;BYDAY=MO,WE;BYSETPOS=-5","20260601T090000",4);
  run("FREQ=MONTHLY;BYDAY=MO;BYSETPOS=9","20260601T090000",4);
  return 0;
}
