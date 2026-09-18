/*
 * Finding 055, defect 2, the confirming experiment. The date libical master
 * returns for an unsatisfiable BYSETPOS is a linear function of
 * ICAL_LIMIT_RECURRENCE_SEARCH, which is what identifies it as the library's
 * own budget rather than an occurrence of the rule. libical 4.x only.
 *   gcc -O2 -I<prefix>/include -o p 055-libical-budget-scaling.c -L<prefix>/lib -lical
 */
#include <stdio.h>
#include <libical/ical.h>
#include <libical/icallimits.h>
static void run(const char *rr, const char *ds, int n){
  struct icalrecurrencetype *r = icalrecurrencetype_new_from_string(rr);
  struct icaltimetype start = icaltime_from_string(ds);
  icalrecur_iterator *it = icalrecur_iterator_new(r, start);
  if(!it){ printf("(no iterator)\n"); return; }
  for(int i=0;i<n;i++){
    struct icaltimetype t = icalrecur_iterator_next(it);
    if(icaltime_is_null_time(t)) { printf("<end> "); break; }
    printf("%s ", icaltime_as_ical_string(t));
  }
  printf("\n"); icalrecur_iterator_free(it);
}
int main(void){
  const char *R="FREQ=WEEKLY;BYDAY=MO,WE;BYSETPOS=5";
  size_t budgets[]={100000,50000,10000,1000};
  for(int i=0;i<4;i++){
    icallimit_set(ICAL_LIMIT_RECURRENCE_SEARCH, budgets[i]);
    printf("budget %7zu -> ", budgets[i]);
    run(R,"20260601T090000",3);
  }
  return 0;
}
