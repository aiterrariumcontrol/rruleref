import net.fortuna.ical4j.model.Recur;

/**
 * Prints which ical4j build the classpath actually resolves, and the jar it came
 * from. Two ical4j jars are vendored (see README.md), and a row on RESULTS.md
 * that names a release is only trustworthy if the run that produced it can say
 * which jar the JVM loaded. Finding 077 is the case where a published table
 * could not. Run this immediately before scoring, with the same -cp.
 */
public final class Ical4jVersion {
    public static void main(String[] args) {
        Package p = Recur.class.getPackage();
        String v = p == null ? null : p.getImplementationVersion();
        Object src = Recur.class.getProtectionDomain().getCodeSource();
        System.out.println("ical4j Implementation-Version: " + (v == null ? "(absent)" : v));
        System.out.println("resolved from: " + (src == null ? "(unknown)" : ((java.security.CodeSource) src).getLocation()));
    }
}
